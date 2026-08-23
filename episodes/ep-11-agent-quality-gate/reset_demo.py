"""Reset the recording Launch to Draft with no pending agent work."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from seed_demo import (
    BPF_ENTITY_SET,
    BPF_NAME,
    TASK_PREFIX,
    Dataverse,
    exactly_one,
    stage,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--launch-name", default="Q3 Widget Launch")
    args = parser.parse_args()

    dv = Dataverse()
    safe_name = args.launch_name.replace("'", "''")
    launch = exactly_one(
        dv.get(
            "/lc_launchs?$select=lc_launchid,lc_name,lc_targetdate"
            f"&$filter=lc_name eq '{safe_name}'&$top=2"
        )["value"],
        f"launch named {args.launch_name!r}",
    )
    launch_id = launch["lc_launchid"]
    workflow = exactly_one(
        dv.get(
            "/workflows?$select=workflowid"
            f"&$filter=name eq '{BPF_NAME}' and category eq 4 and statecode eq 1"
        )["value"],
        f"active {BPF_NAME} BPF",
    )
    draft_id = stage(dv, workflow["workflowid"], "Draft")["processstageid"]
    instance = exactly_one(
        dv.get(
            f"/{BPF_ENTITY_SET}?"
            "$select=businessprocessflowinstanceid"
            f"&$filter=_bpf_lc_launchid_value eq {launch_id} and statecode eq 0"
        )["value"],
        "active Launch Approval instance",
    )
    assignment_key = f"{TASK_PREFIX}{launch_id}"
    safe_key = assignment_key.replace("'", "''")
    tasks = dv.get(
        "/tasks?$select=activityid,statecode"
        f"&$filter=subject eq '{safe_key}'&$top=2"
    )["value"]
    if len(tasks) > 1:
        raise RuntimeError(
            f"Expected at most one Quality Gate assignment; got {len(tasks)}"
        )
    task = tasks[0] if tasks else None
    results = dv.get(
        "/lc_qualitygateresults?$select=lc_qualitygateresultid"
        f"&$filter=lc_assignmentkey eq '{safe_key}'"
    )["value"]
    milestones = dv.get(
        "/lc_milestones?$select=lc_milestoneid,lc_milestonestatus"
        f"&$filter=_lc_launchid_value eq {launch_id}"
    )["value"]
    launch_tasks = dv.get(
        "/lc_tasks?$select=lc_taskid,lc_title,lc_taskstatus"
        f"&$filter=_lc_launchid_value eq {launch_id}"
    )["value"]
    notes = dv.get(
        "/annotations?$select=annotationid"
        f"&$filter=_objectid_value eq {launch_id} "
        "and subject eq 'Quality Gate browser evidence'"
    )["value"]

    if args.dry_run:
        print(
            f"[dry-run] would reset {args.launch_name} to Draft, close any "
            f"assignment, normalize {len(milestones)} milestone(s) and "
            f"{len(launch_tasks)} task(s), clear projected values, delete "
            f"{len(results)} result(s), and remove {len(notes)} evidence note(s)"
        )
        return 0

    if task and task.get("statecode") == 0:
        dv.patch(
            f"/tasks({task['activityid']})",
            {
                "statecode": 1,
                "statuscode": 5,
                "actualend": datetime.now(timezone.utc).isoformat(),
            },
        )
    dv.patch(
        f"/{BPF_ENTITY_SET}({instance['businessprocessflowinstanceid']})",
        {
            "activestageid@odata.bind": f"/processstages({draft_id})",
            "traversedpath": draft_id,
        },
    )
    for result in results:
        dv.delete(
            "/lc_qualitygateresults"
            f"({result['lc_qualitygateresultid']})"
        )
    target_date = launch.get("lc_targetdate")
    if not target_date or target_date < datetime.now(timezone.utc).date().isoformat():
        target_date = (datetime.now(timezone.utc) + timedelta(days=14)).date().isoformat()
    for milestone in milestones:
        if milestone.get("lc_milestonestatus") != 10600204:
            dv.patch(
                f"/lc_milestones({milestone['lc_milestoneid']})",
                {
                    "lc_milestonestatus": 10600202,
                    "lc_duedate": target_date,
                },
            )
    for launch_task in launch_tasks:
        if str(launch_task.get("lc_title") or "").startswith("[Quality Gate]"):
            dv.delete(f"/lc_tasks({launch_task['lc_taskid']})")
        elif launch_task.get("lc_taskstatus") != 10600304:
            dv.patch(
                f"/lc_tasks({launch_task['lc_taskid']})",
                {
                    "lc_taskstatus": 10600302,
                    "lc_isblocked": False,
                    "lc_blockerreason": None,
                    "lc_duedate": target_date,
                },
            )
    for note in notes:
        dv.delete(f"/annotations({note['annotationid']})")
    dv.patch(
        f"/lc_launchs({launch_id})",
        {
            "lc_launchstatus": 10600101,
            "lc_risksummary": "Low. Team reports the launch ready for quality review.",
            "lc_qualitygatestatus": 106000000,
            "lc_qualitygatescore": None,
            "lc_qualitygatefeedback": None,
            "lc_qualitygateevidence": None,
            "lc_qualitygatecheckedon": None,
        },
    )
    dv.post(
        "/lc_statusupdates",
        {
            "lc_title": "Ready for Quality Gate",
            "lc_summary": (
                "Launch team reports Green and On Track. Structured delivery "
                "signals are ready for independent Quality Gate validation."
            ),
            "lc_health": 10600601,
            "lc_postedat": datetime.now(timezone.utc).isoformat(),
            "lc_launchid@odata.bind": f"/lc_launchs({launch_id})",
        },
    )
    print(
        f"[ok] reset {args.launch_name} to Green Draft with no pending agent work"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
