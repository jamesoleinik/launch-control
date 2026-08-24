"""Prove the Agentic User cannot update Launch or move the BPF directly.

The test creates isolated Launch, BPF, and assignment rows with an administrator,
uses genuine Agent User OAuth for the permission probes, and removes its rows.

    python test_agent_permissions_live.py --dry-run
    python test_agent_permissions_live.py --apply
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import requests

from agent.config import Config
from agent.identity import AgentTokenProvider
from test_plugin_live import (
    BPF_NAME,
    BPF_SET,
    TASK_PREFIX,
    LiveTest,
    assert_status,
    exactly_one,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print("Identity: genuine Microsoft Entra Agent User OAuth")
        print("Allowed: read the assigned temporary Launch")
        print("Denied: update Launch and move Launch Approval BPF directly")
        print("Cleanup: assignment, BPF instance, and Launch")
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
            ),
            f"active {BPF_NAME} process",
        )
        process_id = process["workflowid"]
        stages = test.rows(
            "processstages",
            select="processstageid,stagename",
            filter=f"_processid_value eq {process_id}",
        )
        stage_by_name = {
            row["stagename"]: row["processstageid"] for row in stages
        }
        draft_id = stage_by_name["Draft"]
        quality_gate_id = stage_by_name["Quality Gate"]
        approval_id = stage_by_name["Launch Approval"]

        launch_id, _ = test.create(
            "lc_launchs",
            "lc_launch",
            {
                "lc_name": f"Agent permission probe {suffix}",
                "lc_targetdate": (
                    datetime.now(timezone.utc).date() + timedelta(days=30)
                ).isoformat(),
                "lc_qualitygatestatus": 106000000,
            },
        )
        bpf_id, _ = test.create(
            BPF_SET,
            "new_bpf_ae8e29d7071f4eec9ef2a881a1590d5c",
            {
                "bpf_name": f"Agent permission probe {suffix}",
                "bpf_lc_launchid@odata.bind": f"/lc_launchs({launch_id})",
                "processid@odata.bind": f"/workflows({process_id})",
                "activestageid@odata.bind": f"/processstages({draft_id})",
                "traversedpath": draft_id,
            },
        )
        test.request(
            "PATCH",
            f"/{BPF_SET}({bpf_id})",
            body={
                "activestageid@odata.bind": (
                    f"/processstages({quality_gate_id})"
                ),
                "traversedpath": f"{draft_id},{quality_gate_id}",
            },
        )

        assignment_key = f"{TASK_PREFIX}{launch_id}"
        task = exactly_one(
            test.rows(
                "tasks",
                select="activityid,_ownerid_value",
                filter=f"subject eq '{assignment_key}'",
            ),
            "permission probe assignment",
        )
        test.cleanup.append(("tasks", task["activityid"]))
        assert_status(
            "assignment is owned by the configured Agentic User",
            task["_ownerid_value"].lower() == test.agent_id.lower(),
        )

        config = Config.load()
        provider = AgentTokenProvider(config)
        assert_status(
            "permission probe uses genuine Agent User OAuth",
            provider.mode == "Microsoft Entra Agent User OAuth test flow",
        )
        headers = {
            "Authorization": f"Bearer {provider()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        api = config.dataverse_url + "/api/data/v9.2"

        assigned_read = requests.get(
            f"{api}/lc_launchs({launch_id})?$select=lc_name",
            headers=headers,
            timeout=90,
        )
        assert_status(
            "Agentic User can read the assigned Launch",
            assigned_read.status_code == 200,
        )

        denied_launch = requests.patch(
            f"{api}/lc_launchs({launch_id})",
            headers=headers,
            json={"lc_qualitygatescore": 1},
            timeout=90,
        )
        assert_status(
            "Agentic User cannot update Launch directly",
            denied_launch.status_code in (401, 403),
        )

        denied_bpf = requests.patch(
            f"{api}/{BPF_SET}({bpf_id})",
            headers=headers,
            json={
                "activestageid@odata.bind": (
                    f"/processstages({approval_id})"
                ),
                "traversedpath": (
                    f"{draft_id},{quality_gate_id},{approval_id}"
                ),
            },
            timeout=90,
        )
        assert_status(
            "Agentic User cannot move the BPF directly",
            denied_bpf.status_code in (401, 403),
        )
        return 0
    finally:
        test.delete_created()
        print("[PASS] temporary permission probe records removed")


if __name__ == "__main__":
    raise SystemExit(main())
