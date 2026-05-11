"""Force the demo launch into 'perfect launch week' state for Ep 12 recording.

Idempotent. Safe to re-run between takes.
Default --dry-run. Pass --apply to actually mutate.

Sets:
  - launch.lc_launchstatus = ReadyForLaunch
  - every milestone.lc_milestonestatus = Complete
  - every task.lc_taskstatus = Done; clear blockerreason; lc_isblocked = false
  - inserts a fresh 'All gates passed' lc_statusupdate row tagged Ep12Setup::

Use:
  python episodes/ep-12-full-orchestra/orchestra/setup_launch_week.py --dry-run
  python episodes/ep-12-full-orchestra/orchestra/setup_launch_week.py --apply
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import DV, LAUNCH_STATUS, MILESTONE_STATUS, TASK_STATUS  # noqa: E402

SETUP_TAG = 'Ep12Setup::'


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', default=True)
    g.add_argument('--apply', action='store_true')
    p.add_argument('--launch', default=os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch'))
    args = p.parse_args()
    dry = not args.apply

    dv = DV(dry_run=dry)
    print(f"[{'DRY RUN' if dry else 'APPLY'}] perfect-state setup for: {args.launch}")
    print(f"  env: {dv.url}\n")

    launch = dv.find_launch(args.launch)
    lid = launch['lc_launchid']
    cur = launch.get('lc_launchstatus')
    target = LAUNCH_STATUS['ReadyForLaunch']
    if cur != target:
        dv.patch(f"/api/data/v9.2/lc_launchs({lid})",
                 {'lc_launchstatus': target}, label='launch -> ReadyForLaunch')
        print(f"  launch.lc_launchstatus: {cur} -> {target}")
    else:
        print(f"  launch.lc_launchstatus: already ReadyForLaunch ({cur})")

    ms = dv.milestones(lid)
    flipped_m = 0
    for m in ms:
        if m.get('lc_milestonestatus') != MILESTONE_STATUS['Complete']:
            dv.patch(f"/api/data/v9.2/lc_milestones({m['lc_milestoneid']})",
                     {'lc_milestonestatus': MILESTONE_STATUS['Complete']},
                     label=f"milestone {m.get('lc_name','?')[:30]} -> Complete")
            flipped_m += 1
    print(f"  milestones: {flipped_m}/{len(ms)} flipped to Complete")

    tasks = dv.tasks_for_milestones([m['lc_milestoneid'] for m in ms])
    flipped_t = cleared_t = 0
    for t in tasks:
        body: dict = {}
        if t.get('lc_taskstatus') != TASK_STATUS['Done']:
            body['lc_taskstatus'] = TASK_STATUS['Done']; flipped_t += 1
        if t.get('lc_isblocked'):
            body['lc_isblocked'] = False
        if t.get('lc_blockerreason'):
            body['lc_blockerreason'] = None; cleared_t += 1
        if body:
            dv.patch(f"/api/data/v9.2/lc_tasks({t['lc_taskid']})", body,
                     label=f"task {t.get('lc_title','?')[:30]} -> Done")
    print(f"  tasks: {flipped_t}/{len(tasks)} flipped to Done; "
          f"{cleared_t} blockerreasons cleared")

    title = f"{SETUP_TAG}All gates passed"
    body_text = ("Readiness check: every milestone Complete, zero blocked tasks, "
                 "GitHub issues all closed. Verdict: GO.")
    existing = [s for s in dv.get(
        "/api/data/v9.2/lc_statusupdates"
        f"?$select=lc_statusupdateid,lc_title,createdon,_lc_launchid_value"
        f"&$filter=startswith(lc_title,'{SETUP_TAG}')"
        f"&$orderby=createdon desc&$top=20")
        if (s.get('_lc_launchid_value') or '').lower() == lid.lower()]
    if existing:
        print(f"  status updates: {len(existing)} '{SETUP_TAG}' row(s) already present "
              f"(latest: {existing[0]['createdon'][:19]})")
    else:
        dv.post("/api/data/v9.2/lc_statusupdates",
                {'lc_title': title, 'lc_body': body_text,
                 'lc_launchid@odata.bind': f"/lc_launchs({lid})"},
                label='insert all-gates-passed status update')
        print(f"  status updates: inserting fresh '{title}'")

    dv.flush_dry_log()
    print()
    print("DONE." if not dry else "DRY RUN COMPLETE -- pass --apply to write.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
