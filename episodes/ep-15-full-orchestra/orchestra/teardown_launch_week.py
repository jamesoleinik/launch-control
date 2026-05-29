"""Revert the demo launch from 'perfect' back to 'messy mid-launch' for re-rehearsal.

Default --dry-run. Pass --apply to actually mutate.

Restores:
  - launch.lc_launchstatus = InProgress
  - 12 milestones Complete, 2 AtRisk, 2 Blocked (deterministic by name)
  - tasks: ~70% Done, ~20% InProgress, ~10% Blocked (with reasons restored)
  - removes the Ep12Setup:: status update rows added by setup_launch_week.py

Use:
  python episodes/ep-13-full-orchestra/orchestra/teardown_launch_week.py --dry-run
  python episodes/ep-13-full-orchestra/orchestra/teardown_launch_week.py --apply
"""
from __future__ import annotations
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import DV, LAUNCH_STATUS, MILESTONE_STATUS, TASK_STATUS  # noqa: E402

SETUP_TAG = 'Ep12Setup::'

BLOCKER_REASONS = [
    "Waiting on legal sign-off for Apple App Store distribution cert",
    "Synapse downstream consumer needs schema review from data team",
    "Azure AI Search migration blocked on capacity request approval",
    "Marketing creative blocked on photography reshoot",
    "Localization vendor SLA missed; need escalation",
    "Compliance review pending external audit completion",
]


def main() -> int:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', default=True)
    g.add_argument('--apply', action='store_true')
    p.add_argument('--launch', default=os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch'))
    args = p.parse_args()
    dry = not args.apply

    dv = DV(dry_run=dry)
    print(f"[{'DRY RUN' if dry else 'APPLY'}] messy-state teardown for: {args.launch}")
    print(f"  env: {dv.url}\n")

    launch = dv.find_launch(args.launch)
    lid = launch['lc_launchid']
    target = LAUNCH_STATUS['InProgress']
    if launch.get('lc_launchstatus') != target:
        dv.patch(f"/api/data/v9.2/lc_launchs({lid})",
                 {'lc_launchstatus': target}, label='launch -> InProgress')
        print(f"  launch.lc_launchstatus: {launch.get('lc_launchstatus')} -> {target}")
    else:
        print("  launch.lc_launchstatus: already InProgress")

    ms = sorted(dv.milestones(lid),
                key=lambda x: (x.get('lc_name') or '').lower())
    at_risk_idx = {len(ms) - 4, len(ms) - 3}
    blocked_idx = {len(ms) - 2, len(ms) - 1}
    flipped = 0
    for i, m in enumerate(ms):
        if i in blocked_idx:
            tgt = MILESTONE_STATUS['Blocked']
        elif i in at_risk_idx:
            tgt = MILESTONE_STATUS['AtRisk']
        else:
            tgt = MILESTONE_STATUS['Complete']
        if m.get('lc_milestonestatus') != tgt:
            dv.patch(f"/api/data/v9.2/lc_milestones({m['lc_milestoneid']})",
                     {'lc_milestonestatus': tgt},
                     label=f"milestone {m.get('lc_name','?')[:30]} -> {tgt}")
            flipped += 1
    print(f"  milestones: {flipped}/{len(ms)} adjusted "
          f"(target: 12 Complete, 2 AtRisk, 2 Blocked)")

    tasks = dv.tasks_for_milestones([m['lc_milestoneid'] for m in ms])
    tasks_sorted = sorted(tasks, key=lambda x: (x.get('lc_title') or '').lower())
    flipped_t = blocker_set = 0
    for i, t in enumerate(tasks_sorted):
        if i % 10 == 0:
            tgt_status = TASK_STATUS['Blocked']; want_block = True
            reason = BLOCKER_REASONS[i // 10 % len(BLOCKER_REASONS)]
        elif i % 5 == 0:
            tgt_status = TASK_STATUS['InProgress']; want_block = False; reason = None
        else:
            tgt_status = TASK_STATUS['Done']; want_block = False; reason = None
        body: dict = {}
        if t.get('lc_taskstatus') != tgt_status:
            body['lc_taskstatus'] = tgt_status; flipped_t += 1
        if bool(t.get('lc_isblocked')) != want_block:
            body['lc_isblocked'] = want_block
        if (t.get('lc_blockerreason') or None) != reason:
            body['lc_blockerreason'] = reason
            if reason:
                blocker_set += 1
        if body:
            dv.patch(f"/api/data/v9.2/lc_tasks({t['lc_taskid']})", body,
                     label=f"task {t.get('lc_title','?')[:30]}")
    print(f"  tasks: {flipped_t}/{len(tasks)} status-flipped; {blocker_set} blockers re-installed")

    setup_rows = [s for s in dv.get(
        "/api/data/v9.2/lc_statusupdates"
        "?$select=lc_statusupdateid,lc_title,_lc_launchid_value"
        f"&$filter=startswith(lc_title,'{SETUP_TAG}')")
        if (s.get('_lc_launchid_value') or '').lower() == lid.lower()]
    for s in setup_rows:
        dv.delete(f"/api/data/v9.2/lc_statusupdates({s['lc_statusupdateid']})",
                  label=f"remove setup status update {s.get('lc_title')}")
    print(f"  status updates: removing {len(setup_rows)} '{SETUP_TAG}' row(s)")

    dv.flush_dry_log()
    print()
    print("DONE." if not dry else "DRY RUN COMPLETE -- pass --apply to write.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
