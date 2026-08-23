"""Run an isolated real-token integration test for the Quality Gate worker.

The test creates temporary Launch, BPF, task, and result rows, runs the actual
worker, verifies Agent User attribution, then removes only those rows.

    python test_worker_live.py --apply
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from agent.config import Config
from agent.dataverse import DataverseClient
from agent.identity import AgentTokenProvider
from agent.worker import run_once
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
    parser.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    if not args.apply:
        return 1

    test = LiveTest()
    suffix = uuid4().hex[:8]
    try:
        process = exactly_one(
            test.rows(
                "workflows",
                select="workflowid",
                filter=f"name eq '{BPF_NAME}' and category eq 4 and statecode eq 1",
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

        launch_name = f"Quality Gate worker live test {suffix}"
        launch_id, _ = test.create(
            "lc_launchs",
            "lc_launch",
            {
                "lc_name": launch_name,
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
                "bpf_name": f"Quality Gate worker live test {suffix}",
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
                select=(
                    "activityid,_ownerid_value,_regardingobjectid_value,"
                    "statecode,statuscode"
                ),
                filter=f"subject eq '{assignment_key}'",
            ),
            "worker Quality Gate assignment",
        )
        task_id = task["activityid"]
        test.cleanup.append(("tasks", task_id))
        assert_status(
            "assignment is owned by the configured Agent User",
            task["_ownerid_value"].lower() == test.agent_id.lower(),
        )
        assert_status(
            "assignment Regarding is the temporary Launch",
            task["_regardingobjectid_value"].lower() == launch_id.lower(),
        )

        config = Config.load()
        provider = AgentTokenProvider(config)
        assert_status(
            "worker uses the real Agent User OAuth test flow",
            provider.mode == "Microsoft Entra Agent User OAuth test flow",
        )
        client = DataverseClient(config, provider)
        who = client._request("GET", "/WhoAmI").json()
        assert_status(
            "real token resolves to the configured Dataverse Agent User",
            who["UserId"].lower() == test.agent_id.lower(),
        )
        assert_status(
            "worker processed exactly one assignment",
            run_once(client, config) == 1,
        )

        result = exactly_one(
            test.rows(
                "lc_qualitygateresults",
                select=(
                    "lc_qualitygateresultid,lc_outcome,lc_score,"
                    "_createdby_value"
                ),
                filter=f"lc_assignmentkey eq '{assignment_key}'",
            ),
            "worker Quality Gate result",
        )
        result_id = result["lc_qualitygateresultid"]
        test.cleanup.append(("lc_qualitygateresults", result_id))
        assert_status(
            "result createdby is the configured Agent User",
            result["_createdby_value"].lower() == test.agent_id.lower(),
        )
        assert_status(
            "Playwright result passed",
            result["lc_outcome"] == 106000000 and result["lc_score"] == 100,
        )

        launch = exactly_one(
            test.rows(
                "lc_launchs",
                select="lc_qualitygatestatus,lc_qualitygatescore",
                filter=f"lc_launchid eq {launch_id}",
            ),
            "updated Launch",
        )
        assert_status(
            "plug-in projected the passing result onto Launch",
            launch["lc_qualitygatestatus"] == 106000001
            and launch["lc_qualitygatescore"] == 100,
        )
        bpf = exactly_one(
            test.rows(
                BPF_SET,
                select="_activestageid_value",
                filter=f"businessprocessflowinstanceid eq {bpf_id}",
            ),
            "updated BPF instance",
        )
        assert_status(
            "passing result advanced to Launch Approval",
            bpf["_activestageid_value"].lower() == approval_id.lower(),
        )
        completed_task = exactly_one(
            test.rows(
                "tasks",
                select="statecode,statuscode",
                filter=f"activityid eq {task_id}",
            ),
            "completed assignment",
        )
        assert_status(
            "worker completed the assignment",
            completed_task["statecode"] == 1
            and completed_task["statuscode"] == 5,
        )
        print("[PASS] real Agent User Playwright worker integration")
        return 0
    finally:
        test.delete_created()


if __name__ == "__main__":
    raise SystemExit(main())
