"""Run an isolated Agentic User MCP write-through test for the BPF."""

import json
import os
import time
import argparse
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import requests


DV_URL = os.environ.get("DV_URL", "").rstrip("/")
API_URL = f"{DV_URL}/api/data/v9.2"
MCP_URL = f"{DV_URL}/api/mcp"
TENANT_ID = os.environ.get("TENANT_ID", "")
BLUEPRINT_CLIENT_ID = os.environ.get("A365_BLUEPRINT_CLIENT_ID", "")
BLUEPRINT_SECRET = os.environ.get("A365_BLUEPRINT_CLIENT_SECRET", "")
AGENT_ID = os.environ.get("A365_AGENT_ID", "")
AGENT_USER_ID = os.environ.get("A365_AGENT_USER_ID", "")
AGENT_SYSTEMUSER_ID = os.environ.get(
    "QUALITY_GATE_AGENT_SYSTEMUSER_ID", ""
).strip("{}")
ADMIN_TOKEN = os.environ.get("DV_ADMIN_TOKEN", "")

BPF_NAME = "Launch Approval"
BPF_SET = "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5cs"
TASK_PREFIX = "Quality Gate::"
CLIENT_ASSERTION_TYPE = (
    "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
)

ADMIN_HEADERS = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    "OData-MaxVersion": "4.0",
    "OData-Version": "4.0",
}


def check(label, condition):
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}", flush=True)


def admin_request(method, path, body=None, expected=(200, 201, 204)):
    response = requests.request(
        method,
        API_URL + path,
        headers=ADMIN_HEADERS,
        json=body,
        timeout=120,
    )
    if response.status_code not in expected:
        raise RuntimeError(
            f"{method} {path} returned {response.status_code}: "
            f"{response.text[:800]}"
        )
    return response


def rows(table, select, filter_text, top=10):
    response = requests.get(
        f"{API_URL}/{table}",
        headers=ADMIN_HEADERS,
        params={
            "$select": select,
            "$filter": filter_text,
            "$top": top,
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"GET {table} returned {response.status_code}: "
            f"{response.text[:800]}"
        )
    return response.json().get("value", [])


def exactly_one(items, description):
    if len(items) != 1:
        raise AssertionError(
            f"Expected exactly one {description}; got {len(items)}"
        )
    return items[0]


def entity_id(response):
    value = response.headers.get("OData-EntityId", "")
    if "(" in value:
        return value.rsplit("(", 1)[-1].rstrip(")")
    payload = response.json() if response.content else {}
    for name, value in payload.items():
        if name.endswith("id") and isinstance(value, str):
            return value
    raise RuntimeError("Create response returned no entity ID")


def token_request(form, description):
    response = requests.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data=form,
        timeout=60,
    )
    payload = response.json()
    if response.status_code != 200:
        raise RuntimeError(
            f"{description} failed ({response.status_code}, "
            f"{payload.get('error', 'unknown')})"
        )
    return payload["access_token"]


def agent_user_mcp_token():
    exchange_scope = "api://AzureADTokenExchange/.default"
    blueprint_token = token_request(
        {
            "client_id": BLUEPRINT_CLIENT_ID,
            "scope": exchange_scope,
            "grant_type": "client_credentials",
            "client_secret": BLUEPRINT_SECRET,
            "fmi_path": AGENT_ID,
        },
        "blueprint exchange",
    )
    agent_token = token_request(
        {
            "client_id": AGENT_ID,
            "scope": exchange_scope,
            "grant_type": "client_credentials",
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": blueprint_token,
        },
        "Agent Identity exchange",
    )
    return token_request(
        {
            "client_id": AGENT_ID,
            "scope": f"{DV_URL}/api/mcp/mcp.tools",
            "grant_type": "user_fic",
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "client_assertion": blueprint_token,
            "user_id": AGENT_USER_ID,
            "user_federated_identity_credential": agent_token,
        },
        "Agentic User MCP resource token",
    )


class McpClient:
    def __init__(self, token):
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        self.request_id = 0

    @staticmethod
    def parse(response):
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            payload = None
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    payload = json.loads(line[5:].strip())
            return payload
        return response.json()

    def rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self.request_id += 1
            body["id"] = self.request_id
        if params is not None:
            body["params"] = params
        response = self.session.post(
            MCP_URL,
            headers=self.headers,
            data=json.dumps(body),
            timeout=180,
        )
        response.raise_for_status()
        session_id = response.headers.get("Mcp-Session-Id")
        if session_id:
            self.headers["Mcp-Session-Id"] = session_id
        return None if notify else self.parse(response)

    def initialize(self):
        result = self.rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "launch-control-mcp-bpf-test",
                    "version": "1.0",
                },
            },
        )
        self.rpc("notifications/initialized", notify=True)
        return result

    def create_record(self, table, item):
        response = self.rpc(
            "tools/call",
            {
                "name": "create_record",
                "arguments": {
                    "tablename": table,
                    "item": json.dumps(item),
                },
            },
        )
        result = (response or {}).get("result", {})
        text = "".join(
            part.get("text", "")
            for part in result.get("content", [])
            if part.get("type") == "text"
        )
        if result.get("isError"):
            raise RuntimeError(f"MCP create_record failed: {text[:800]}")
        return text


def wait_for_one(table, select, filter_text, description, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = rows(table, select, filter_text)
        if len(found) == 1:
            return found[0]
        time.sleep(1)
    return exactly_one(
        rows(table, select, filter_text), description
    )


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print("Live path: Agentic User -> MCP create_record -> result plug-in")
        print("Checks: attribution, Launch projection, BPF stage, access revocation")
        print("Cleanup: result, task, BPF instance, Launch")
        return
    required = {
        "DV_URL": DV_URL,
        "TENANT_ID": TENANT_ID,
        "A365_BLUEPRINT_CLIENT_ID": BLUEPRINT_CLIENT_ID,
        "A365_BLUEPRINT_CLIENT_SECRET": BLUEPRINT_SECRET,
        "A365_AGENT_ID": AGENT_ID,
        "A365_AGENT_USER_ID": AGENT_USER_ID,
        "QUALITY_GATE_AGENT_SYSTEMUSER_ID": AGENT_SYSTEMUSER_ID,
        "DV_ADMIN_TOKEN": ADMIN_TOKEN,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing live-test configuration: " + ", ".join(missing)
        )

    cleanup = []
    suffix = uuid4().hex[:8]
    try:
        process = exactly_one(
            rows(
                "workflows",
                "workflowid",
                f"name eq '{BPF_NAME}' and category eq 4 and statecode eq 1",
            ),
            f"active {BPF_NAME} workflow",
        )
        process_id = process["workflowid"]
        stages = rows(
            "processstages",
            "processstageid,stagename",
            f"_processid_value eq {process_id}",
        )
        stage_ids = {
            stage["stagename"]: stage["processstageid"] for stage in stages
        }
        draft_id = stage_ids["Draft"]
        quality_gate_id = stage_ids["Quality Gate"]
        approval_id = stage_ids["Launch Approval"]

        launch_response = admin_request(
            "POST",
            "/lc_launchs",
            {
                "lc_name": f"MCP BPF validation {suffix}",
                "lc_targetdate": (
                    datetime.now(timezone.utc).date() + timedelta(days=30)
                ).isoformat(),
                "lc_qualitygatestatus": 106000000,
            },
        )
        launch_id = entity_id(launch_response)
        cleanup.append(("lc_launchs", launch_id))

        bpf_response = admin_request(
            "POST",
            f"/{BPF_SET}",
            {
                "bpf_name": f"MCP BPF validation {suffix}",
                "bpf_lc_launchid@odata.bind": f"/lc_launchs({launch_id})",
                "processid@odata.bind": f"/workflows({process_id})",
                "activestageid@odata.bind": f"/processstages({draft_id})",
                "traversedpath": draft_id,
            },
        )
        bpf_id = entity_id(bpf_response)
        cleanup.append((BPF_SET, bpf_id))

        admin_request(
            "PATCH",
            f"/{BPF_SET}({bpf_id})",
            {
                "activestageid@odata.bind": (
                    f"/processstages({quality_gate_id})"
                ),
                "traversedpath": f"{draft_id},{quality_gate_id}",
            },
        )

        assignment_key = f"{TASK_PREFIX}{launch_id}"
        task = wait_for_one(
            "tasks",
            "activityid,_ownerid_value,_regardingobjectid_value",
            f"subject eq '{assignment_key}'",
            "Quality Gate assignment",
        )
        task_id = task["activityid"]
        cleanup.append(("tasks", task_id))
        check(
            "Quality Gate entry assigned the Agentic User",
            task["_ownerid_value"].lower()
            == AGENT_SYSTEMUSER_ID.lower(),
        )
        check(
            "assignment is related to the temporary Launch",
            task["_regardingobjectid_value"].lower() == launch_id.lower(),
        )

        token = agent_user_mcp_token()
        client = McpClient(token)
        init = client.initialize()
        check(
            "Agentic User initialized the Dataverse MCP server",
            (init or {}).get("result", {}).get("serverInfo") is not None,
        )

        checked_on = datetime.now(timezone.utc).isoformat()
        client.create_record(
            "lc_qualitygateresult",
            {
                "lc_name": f"MCP passing result {suffix}",
                "lc_outcome": 106000000,
                "lc_score": 93,
                "lc_checkedon": checked_on,
                "lc_feedback": (
                    "Agentic User submitted this passing result through "
                    "Dataverse MCP."
                ),
                "lc_evidence": "mcp://agent-user-bpf-validation",
                "lc_assignmentkey": assignment_key,
                "lc_launch": json.dumps(
                    {
                        "relatedTable": "lc_launch",
                        "recordId": launch_id,
                    }
                ),
            },
        )

        result = wait_for_one(
            "lc_qualitygateresults",
            "lc_qualitygateresultid,_createdby_value,lc_outcome,lc_score",
            f"lc_assignmentkey eq '{assignment_key}'",
            "MCP-created Quality Gate result",
        )
        result_id = result["lc_qualitygateresultid"]
        cleanup.append(("lc_qualitygateresults", result_id))
        check(
            "MCP result is attributed to the Agentic User",
            result["_createdby_value"].lower()
            == AGENT_SYSTEMUSER_ID.lower(),
        )
        check(
            "MCP preserved the passing outcome and score",
            result["lc_outcome"] == 106000000
            and result["lc_score"] == 93,
        )

        launch = exactly_one(
            rows(
                "lc_launchs",
                "lc_qualitygatestatus,lc_qualitygatescore",
                f"lc_launchid eq {launch_id}",
            ),
            "updated Launch",
        )
        check(
            "plug-in projected the MCP result to the Launch",
            launch["lc_qualitygatestatus"] == 106000001
            and launch["lc_qualitygatescore"] == 93,
        )

        bpf = exactly_one(
            rows(
                BPF_SET,
                "_activestageid_value",
                f"businessprocessflowinstanceid eq {bpf_id}",
            ),
            "updated BPF instance",
        )
        check(
            "plug-in advanced the BPF to Launch Approval",
            bpf["_activestageid_value"].lower() == approval_id.lower(),
        )

        agent_headers = dict(ADMIN_HEADERS)
        agent_headers["Authorization"] = f"Bearer {token}"
        denied = requests.get(
            f"{API_URL}/lc_launchs({launch_id})?$select=lc_name",
            headers=agent_headers,
            timeout=120,
        )
        check(
            "plug-in revoked assignment-scoped Launch access",
            denied.status_code in (401, 403, 404),
        )

        print(
            "[PASS] Agentic User MCP result triggered the governed BPF action",
            flush=True,
        )
    finally:
        failures = []
        for table_set, record_id in reversed(cleanup):
            response = requests.delete(
                f"{API_URL}/{table_set}({record_id})",
                headers=ADMIN_HEADERS,
                timeout=120,
            )
            if response.status_code not in (204, 404):
                failures.append(
                    f"{table_set}({record_id}): {response.status_code}"
                )
        if failures:
            raise RuntimeError(
                "Temporary cleanup failed: " + ", ".join(failures)
            )
        print("[PASS] temporary MCP BPF test records removed", flush=True)


if __name__ == "__main__":
    main()
