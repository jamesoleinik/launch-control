"""Enter Quality Gate for the demo launch and let the plug-in assign it."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import auth  # noqa: E402

EPISODE = "ep-11-agent-quality-gate"
TASK_PREFIX = "Quality Gate::"
BPF_NAME = "Launch Approval"
BPF_ENTITY_SET = "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5cs"


class Dataverse:
    def __init__(self) -> None:
        auth.load_env(EPISODE)
        self.url = os.environ["DATAVERSE_URL"].rstrip("/")
        self.api = self.url + "/api/data/v9.2"
        token = auth.get_token(EPISODE)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }

    def get(self, path: str) -> dict[str, Any]:
        response = requests.get(self.api + path, headers=self.headers, timeout=90)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, body: dict[str, Any]) -> requests.Response:
        response = requests.post(
            self.api + path, headers=self.headers, json=body, timeout=90
        )
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"POST {path} failed ({response.status_code}): {response.text[:600]}"
            )
        return response

    def patch(self, path: str, body: dict[str, Any]) -> None:
        response = requests.patch(
            self.api + path, headers=self.headers, json=body, timeout=90
        )
        if response.status_code != 204:
            raise RuntimeError(
                f"PATCH {path} failed ({response.status_code}): "
                f"{response.text[:600]}"
            )

    def delete(self, path: str) -> None:
        response = requests.delete(
            self.api + path, headers=self.headers, timeout=90
        )
        if response.status_code not in (204, 404):
            raise RuntimeError(
                f"DELETE {path} failed ({response.status_code}): "
                f"{response.text[:600]}"
            )


def exactly_one(rows: list[dict[str, Any]], description: str) -> dict[str, Any]:
    if len(rows) != 1:
        raise SystemExit(f"Expected exactly one {description}; got {len(rows)}")
    return rows[0]


def stage(dv: Dataverse, workflow_id: str, name: str) -> dict[str, Any]:
    safe_name = name.replace("'", "''")
    rows = dv.get(
        "/processstages?$select=processstageid,stagename"
        f"&$filter=_processid_value eq {workflow_id} "
        f"and stagename eq '{safe_name}'"
    )["value"]
    return exactly_one(rows, f"{name} process stage")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--launch-name",
        default=os.environ.get("LAUNCH_CONTROL_LAUNCH_NAME", "Q3 Widget Launch"),
    )
    args = parser.parse_args()

    dv = Dataverse()
    safe_name = args.launch_name.replace("'", "''")
    launches = dv.get(
        "/lc_launchs?$select=lc_launchid,lc_name"
        f"&$filter=lc_name eq '{safe_name}'&$top=2"
    )["value"]
    launch = exactly_one(
        launches, f"launch named {args.launch_name!r}"
    )
    launch_id = launch["lc_launchid"]
    assignment_key = f"{TASK_PREFIX}{launch_id}"
    safe_key = assignment_key.replace("'", "''")
    existing_results = dv.get(
        "/lc_qualitygateresults?$select=lc_qualitygateresultid"
        f"&$filter=lc_assignmentkey eq '{safe_key}'&$top=1"
    )["value"]
    workflows = dv.get(
        "/workflows?$select=workflowid,name"
        f"&$filter=name eq '{BPF_NAME}' and category eq 4 and statecode eq 1"
    )["value"]
    workflow = exactly_one(workflows, f"active {BPF_NAME} BPF")
    workflow_id = workflow["workflowid"]
    draft = stage(dv, workflow_id, "Draft")
    quality_gate = stage(dv, workflow_id, "Quality Gate")
    instances = dv.get(
        f"/{BPF_ENTITY_SET}?"
        "$select=businessprocessflowinstanceid,_activestageid_value,traversedpath"
        f"&$filter=_bpf_lc_launchid_value eq {launch_id} and statecode eq 0"
    )["value"]
    if len(instances) > 1:
        raise SystemExit(
            f"Expected at most one active BPF instance; got {len(instances)}"
        )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "launch": launch["lc_name"],
                    "process": BPF_NAME,
                    "current_instance": bool(instances),
                    "target_stage": "Quality Gate",
                    "assignment_key": assignment_key,
                    "existing_result": bool(existing_results),
                },
                indent=2,
            )
        )
        return 0

    if existing_results:
        raise SystemExit(
            "A Quality Gate Result already exists. Run reset_demo.py --apply "
            "before re-entering Quality Gate."
        )

    draft_id = draft["processstageid"]
    quality_gate_id = quality_gate["processstageid"]
    if not instances:
        response = dv.post(
            f"/{BPF_ENTITY_SET}",
            {
                "bpf_name": f"{BPF_NAME}: {launch['lc_name']}",
                "bpf_lc_launchid@odata.bind": f"/lc_launchs({launch_id})",
                "processid@odata.bind": f"/workflows({workflow_id})",
                "activestageid@odata.bind": f"/processstages({draft_id})",
                "traversedpath": draft_id,
            },
        )
        entity_id = response.headers.get("OData-EntityId", "")
        instance_id = entity_id.rsplit("(", 1)[-1].rstrip(")")
        traversed_path = draft_id
        print("[ok] created Launch Approval process instance")
    else:
        instance = instances[0]
        instance_id = instance["businessprocessflowinstanceid"]
        traversed_path = instance.get("traversedpath") or draft_id

    stages = [
        value.strip().strip("{}")
        for value in traversed_path.split(",")
        if value.strip()
    ]
    quality_gate_index = next(
        (
            index
            for index, stage_id in enumerate(stages)
            if stage_id.lower() == quality_gate_id.lower()
        ),
        None,
    )
    if quality_gate_index is None:
        stages.append(quality_gate_id)
    else:
        stages = stages[: quality_gate_index + 1]
    traversed_path = ",".join(stages)
    dv.patch(
        f"/{BPF_ENTITY_SET}({instance_id})",
        {
            "activestageid@odata.bind": (
                f"/processstages({quality_gate_id})"
            ),
            "traversedpath": traversed_path,
        },
    )
    assignments = dv.get(
        "/tasks?$select=activityid,subject,statecode,_ownerid_value"
        f"&$filter=subject eq '{safe_key}'&$top=2"
    )["value"]
    assignment = exactly_one(assignments, "Quality Gate assignment")
    print(f"[ok] Quality Gate assignment: {assignment['activityid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
