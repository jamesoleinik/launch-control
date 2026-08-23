"""Run isolated live integration tests for the Quality Gate plug-in.

The test creates temporary Launch, BPF, task, and result rows, then removes
only those rows in a finally block.

    python test_plugin_live.py --dry-run
    python test_plugin_live.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import auth  # noqa: E402

EPISODE = "ep-11-agent-quality-gate"
BPF_NAME = "Launch Approval"
BPF_SET = "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5cs"
TASK_PREFIX = "Quality Gate::"
OUTCOMES = [
    ("Passed", 106000000, 106000001, "Launch Approval"),
    ("Failed", 106000001, 106000002, "Quality Gate"),
    ("Needs review", 106000002, 106000003, "Quality Gate"),
    ("Error", 106000003, 106000004, "Quality Gate"),
]


class LiveTest:
    def __init__(self) -> None:
        auth.load_env(EPISODE)
        self.url = os.environ["DATAVERSE_URL"].rstrip("/")
        self.api = self.url + "/api/data/v9.2"
        self.agent_id = os.environ[
            "QUALITY_GATE_AGENT_SYSTEMUSER_ID"
        ].strip("{}")
        token = auth.get_token(EPISODE)
        self.admin_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        self.agent_headers = dict(
            self.admin_headers,
            MSCRMCallerID=self.agent_id,
        )
        self.cleanup: list[tuple[str, str]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        agent: bool = False,
        expected: tuple[int, ...] = (200, 201, 204),
        prefer_representation: bool = False,
    ) -> requests.Response:
        headers = dict(
            self.agent_headers if agent else self.admin_headers
        )
        if prefer_representation:
            headers["Prefer"] = "return=representation"
        response = requests.request(
            method,
            self.api + path,
            headers=headers,
            json=body,
            timeout=120,
        )
        if response.status_code not in expected:
            raise RuntimeError(
                f"{method} {path} returned {response.status_code}: "
                f"{response.text[:1000]}"
            )
        return response

    def rows(
        self,
        table: str,
        *,
        select: str,
        filter: str,
        top: int = 10,
    ) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.api}/{table}",
            headers=self.admin_headers,
            params={
                "$select": select,
                "$filter": filter,
                "$top": top,
            },
            timeout=120,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"GET {table} returned {response.status_code}: "
                f"{response.text[:1000]}"
            )
        return response.json().get("value", [])

    @staticmethod
    def entity_id(response: requests.Response) -> str:
        entity_url = response.headers.get("OData-EntityId", "")
        if "(" in entity_url:
            return entity_url.rsplit("(", 1)[-1].rstrip(")")
        if response.content:
            payload = response.json()
            for name, value in payload.items():
                if name.endswith("id") and isinstance(value, str):
                    return value
        raise RuntimeError("Dataverse create returned no entity ID")

    def create(
        self,
        table_set: str,
        logical_name: str,
        body: dict[str, Any],
        *,
        agent: bool = False,
        prefer_representation: bool = False,
    ) -> tuple[str, requests.Response]:
        response = self.request(
            "POST",
            f"/{table_set}",
            body=body,
            agent=agent,
            prefer_representation=prefer_representation,
        )
        entity_id = self.entity_id(response)
        self.cleanup.append((table_set, entity_id))
        return entity_id, response

    def delete_created(self) -> None:
        failures = []
        for table_set, entity_id in reversed(self.cleanup):
            response = requests.delete(
                f"{self.api}/{table_set}({entity_id})",
                headers=self.admin_headers,
                timeout=120,
            )
            if response.status_code not in (204, 404):
                failures.append(
                    f"{table_set}({entity_id}): {response.status_code}"
                )
        if failures:
            raise RuntimeError(
                "Temporary cleanup failed: " + ", ".join(failures)
            )


def exactly_one(
    rows: list[dict[str, Any]], description: str
) -> dict[str, Any]:
    if len(rows) != 1:
        raise AssertionError(
            f"Expected exactly one {description}; got {len(rows)}"
        )
    return rows[0]


def assert_status(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"[PASS] {label}")


def run_case(
    test: LiveTest,
    suffix: str,
    process_id: str,
    draft_id: str,
    quality_gate_id: str,
    outcome_name: str,
    outcome_value: int,
    launch_status: int,
    expected_stage: str,
) -> None:
    launch_id, _ = test.create(
        "lc_launchs",
        "lc_launch",
        {
            "lc_name": f"Quality Gate live test {outcome_name} {suffix}",
            "lc_targetdate": (
                datetime.now(timezone.utc).date() + timedelta(days=30)
            ).isoformat(),
            "lc_qualitygatestatus": 106000000,
        },
    )
    instance_id, _ = test.create(
        BPF_SET,
        "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5c",
        {
            "bpf_name": f"Quality Gate live test {outcome_name}",
            "bpf_lc_launchid@odata.bind": f"/lc_launchs({launch_id})",
            "processid@odata.bind": f"/workflows({process_id})",
            "activestageid@odata.bind": f"/processstages({draft_id})",
            "traversedpath": draft_id,
        },
    )
    denied_before_assignment = test.request(
        "GET",
        f"/lc_launchs({launch_id})?$select=lc_name",
        agent=True,
        expected=(401, 403, 404),
    )
    assert_status(
        f"{outcome_name}: agent cannot read Launch before assignment",
        denied_before_assignment.status_code in (401, 403, 404),
    )
    traversed = f"{draft_id},{quality_gate_id}"
    test.request(
        "PATCH",
        f"/{BPF_SET}({instance_id})",
        body={
            "activestageid@odata.bind": (
                f"/processstages({quality_gate_id})"
            ),
            "traversedpath": traversed,
        },
    )

    assignment_key = f"{TASK_PREFIX}{launch_id}"
    tasks = test.rows(
        "tasks",
        select=(
            "activityid,_ownerid_value,_regardingobjectid_value,statecode"
        ),
        filter=f"subject eq '{assignment_key}'",
        top=2,
    )
    task = exactly_one(tasks, f"{outcome_name} assignment")
    task_id = task["activityid"]
    test.cleanup.append(("tasks", task_id))
    assert_status(
        f"{outcome_name}: assignment owner is Agentic User",
        task.get("_ownerid_value", "").lower()
        == test.agent_id.lower(),
    )
    assert_status(
        f"{outcome_name}: assignment Regarding is Launch",
        task.get("_regardingobjectid_value", "").lower()
        == launch_id.lower(),
    )
    assigned_launch = test.request(
        "GET",
        f"/lc_launchs({launch_id})?$select=lc_name",
        agent=True,
    )
    assert_status(
        f"{outcome_name}: assignment grants agent Launch read access",
        assigned_launch.json().get("lc_name", "").startswith(
            "Quality Gate live test"
        ),
    )

    test.request(
        "PATCH",
        f"/{BPF_SET}({instance_id})",
        body={
            "activestageid@odata.bind": (
                f"/processstages({quality_gate_id})"
            ),
            "traversedpath": traversed,
        },
    )
    duplicate_tasks = test.rows(
        "tasks",
        select="activityid",
        filter=f"subject eq '{assignment_key}'",
        top=2,
    )
    assert_status(
        f"{outcome_name}: assignment is idempotent",
        len(duplicate_tasks) == 1,
    )

    denied_launch = test.request(
        "PATCH",
        f"/lc_launchs({launch_id})",
        body={"lc_qualitygatescore": 1},
        agent=True,
        expected=(401, 403),
    )
    assert_status(
        f"{outcome_name}: agent cannot update Launch directly",
        denied_launch.status_code in (401, 403),
    )

    result_body = {
        "lc_name": f"{outcome_name} live result",
        "lc_outcome": outcome_value,
        "lc_score": 90,
        "lc_checkedon": datetime.now(timezone.utc).isoformat(),
        "lc_feedback": f"Live integration result: {outcome_name}",
        "lc_evidence": "plugin://live-integration-test",
        "lc_assignmentkey": assignment_key,
        "lc_Launch@odata.bind": f"/lc_launchs({launch_id})",
    }
    unauthorized = test.request(
        "POST",
        "/lc_qualitygateresults",
        body=result_body,
        expected=(400,),
    )
    assert_status(
        f"{outcome_name}: non-owner result is rejected",
        unauthorized.status_code == 400,
    )

    result_id, response = test.create(
        "lc_qualitygateresults",
        "lc_qualitygateresult",
        result_body,
        agent=True,
        prefer_representation=True,
    )
    created_by = response.json().get("_createdby_value")
    assert_status(
        f"{outcome_name}: result attribution is Agentic User",
        bool(created_by)
        and created_by.lower() == test.agent_id.lower(),
    )
    denied_after_result = test.request(
        "GET",
        f"/lc_launchs({launch_id})?$select=lc_name",
        agent=True,
        expected=(401, 403, 404),
    )
    assert_status(
        f"{outcome_name}: result completion revokes Launch read access",
        denied_after_result.status_code in (401, 403, 404),
    )

    launch = exactly_one(
        test.rows(
            "lc_launchs",
            select="lc_qualitygatestatus,lc_qualitygatescore",
            filter=f"lc_launchid eq {launch_id}",
            top=1,
        ),
        f"{outcome_name} Launch",
    )
    assert_status(
        f"{outcome_name}: result projected to Launch",
        launch.get("lc_qualitygatestatus") == launch_status
        and launch.get("lc_qualitygatescore") == 90,
    )

    instance = exactly_one(
        test.rows(
            BPF_SET,
            select="_activestageid_value",
            filter=f"businessprocessflowinstanceid eq {instance_id}",
            top=1,
        ),
        f"{outcome_name} BPF instance",
    )
    active_stage_id = instance.get("_activestageid_value")
    active_stage = exactly_one(
        test.rows(
            "processstages",
            select="stagename",
            filter=f"processstageid eq {active_stage_id}",
            top=1,
        ),
        f"{outcome_name} active stage",
    )
    assert_status(
        f"{outcome_name}: BPF stage is {expected_stage}",
        active_stage.get("stagename") == expected_stage,
    )

    duplicate = test.request(
        "POST",
        "/lc_qualitygateresults",
        body=result_body,
        agent=True,
        expected=(400, 401, 403),
    )
    assert_status(
        f"{outcome_name}: duplicate result is rejected",
        duplicate.status_code in (400, 401, 403),
    )
    results = test.rows(
        "lc_qualitygateresults",
        select="lc_qualitygateresultid",
        filter=f"lc_assignmentkey eq '{assignment_key}'",
        top=2,
    )
    assert_status(
        f"{outcome_name}: duplicate result rolled back",
        len(results) == 1
        and results[0]["lc_qualitygateresultid"] == result_id,
    )

    test.request(
        "PATCH",
        f"/tasks({task_id})",
        body={
            "statecode": 1,
            "statuscode": 5,
            "actualend": datetime.now(timezone.utc).isoformat(),
        },
        agent=True,
    )
    completed = exactly_one(
        test.rows(
            "tasks",
            select="statecode,statuscode",
            filter=f"activityid eq {task_id}",
            top=1,
        ),
        f"{outcome_name} completed assignment",
    )
    assert_status(
        f"{outcome_name}: agent completed its assignment",
        completed.get("statecode") == 1
        and completed.get("statuscode") == 5,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print("Live matrix: Passed, Failed, Needs review, Error")
        print("Checks: assignment, idempotency, authorization, projection, stage")
        print("Cleanup: result, task, BPF instance, Launch")
        return 0

    test = LiveTest()
    suffix = uuid4().hex[:8]
    try:
        process = exactly_one(
            test.rows(
                "workflows",
                select="workflowid",
                filter=(
                    f"name eq '{BPF_NAME}' and category eq 4 "
                    "and statecode eq 1"
                ),
                top=2,
            ),
            f"active {BPF_NAME} workflow",
        )
        process_id = process["workflowid"]
        draft = exactly_one(
            test.rows(
                "processstages",
                select="processstageid",
                filter=(
                    f"_processid_value eq {process_id} "
                    "and stagename eq 'Draft'"
                ),
                top=2,
            ),
            "Draft stage",
        )
        quality_gate = exactly_one(
            test.rows(
                "processstages",
                select="processstageid",
                filter=(
                    f"_processid_value eq {process_id} "
                    "and stagename eq 'Quality Gate'"
                ),
                top=2,
            ),
            "Quality Gate stage",
        )
        for case in OUTCOMES:
            run_case(
                test,
                suffix,
                process_id,
                draft["processstageid"],
                quality_gate["processstageid"],
                *case,
            )
        print("[PASS] complete live Quality Gate plug-in matrix")
        return 0
    finally:
        test.delete_created()
        print("[PASS] temporary live-test records removed")


if __name__ == "__main__":
    raise SystemExit(main())
