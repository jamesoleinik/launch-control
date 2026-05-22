"""Episode 10 preflight: verify the demo data is rich enough for the gen-page recording.

Checks:
  - Q3 Widget Launch exists
  - >=16 milestones linked to it
  - >=50 tasks total, all linked to launch milestones (no orphans)
  - >=4 task-status buckets populated (NotStarted / InProgress / Blocked / Done)
  - >=3 cards per kanban column (so no column looks empty on camera)
  - Every Q3 task has an owner (so kanban cards show a person chip)
  - Every Blocked Q3 task has a blockerreason (so the red banner has content)
  - >=8 status updates exist
  - Cloud flows that were causing duplicate-task creation are disabled

Run: python episodes/ep-10-the-dashboard/preflight.py
"""
import os, sys, requests
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts'))
from dotenv import load_dotenv
from auth import get_credential

load_dotenv()
URL = os.environ['DATAVERSE_URL']
TOK = get_credential().get_token(URL + '/.default').token
H = {'Authorization': 'Bearer ' + TOK, 'Accept': 'application/json'}


def fetch(path):
    full = URL + path
    out = []
    while full:
        r = requests.get(full, headers=H)
        r.raise_for_status()
        j = r.json()
        out.extend(j.get('value', []))
        full = j.get('@odata.nextLink')
    return out


def check(name, ok, detail=''):
    icon = '✅' if ok else '❌'
    print(f"  {icon}  {name}{(' — ' + detail) if detail else ''}")
    return ok


def main():
    print("Episode 10 preflight\n")
    failures = 0

    launches = fetch("/api/data/v9.2/lc_launchs?$select=lc_launchid,lc_name&$filter=lc_name eq 'Q3 Widget Launch'")
    if not check("Q3 Widget Launch exists", len(launches) == 1, f"found {len(launches)}"):
        return 1
    lid = launches[0]['lc_launchid']

    ms = fetch(f"/api/data/v9.2/lc_milestones?$select=lc_milestoneid&$filter=_lc_launchid_value eq {lid}")
    if not check("Milestones linked to launch >= 16", len(ms) >= 16, f"got {len(ms)}"):
        failures += 1
    ms_ids = {m['lc_milestoneid'] for m in ms}

    tasks = fetch("/api/data/v9.2/lc_tasks?$select=lc_taskid,_lc_milestoneid_value,_lc_assignedtoid_value,lc_taskstatus,lc_isblocked,lc_blockerreason")
    linked = [t for t in tasks if t.get('_lc_milestoneid_value') in ms_ids]
    if not check("Tasks total >= 50", len(tasks) >= 50, f"got {len(tasks)}"):
        failures += 1
    if not check("All tasks linked to launch milestones", len(linked) == len(tasks),
                 f"{len(linked)}/{len(tasks)} linked"):
        failures += 1

    status_counts = Counter(t.get('lc_taskstatus') for t in linked)
    populated = sum(1 for v in status_counts.values() if v > 0)
    if not check(">=4 task-status buckets populated", populated >= 4,
                 f"buckets={dict(status_counts)}"):
        failures += 1

    # Gen-page kanban depth: each column >=3 so no card column looks empty on camera.
    KANBAN = {10600020: "NotStarted", 10600021: "InProgress", 10600023: "Blocked", 10600022: "Done"}
    for code, label in KANBAN.items():
        cnt = status_counts.get(code, 0)
        if not check(f"Kanban column '{label}' >= 3", cnt >= 3, f"got {cnt}"):
            failures += 1

    with_owner = sum(1 for t in linked if t.get('_lc_assignedtoid_value'))
    if not check("Every Q3 task has an owner", with_owner == len(linked),
                 f"{with_owner}/{len(linked)} owned"):
        failures += 1

    blocked_q3 = [t for t in linked if t.get('lc_taskstatus') == 10600023]
    blocked_with_reason = sum(1 for t in blocked_q3 if t.get('lc_blockerreason'))
    if not check("Every Blocked Q3 task has blockerreason",
                 blocked_with_reason == len(blocked_q3),
                 f"{blocked_with_reason}/{len(blocked_q3)} have reason"):
        failures += 1

    sus = fetch("/api/data/v9.2/lc_statusupdates?$select=lc_statusupdateid")
    if not check("Status updates >= 8", len(sus) >= 8, f"got {len(sus)}"):
        failures += 1

    flow_ids = [
        "eb714d2e-8a49-f111-bec6-00224805fb16",
        "349f7ce4-1545-f111-bec6-00224805ff5f",
    ]
    disabled = 0
    for fid in flow_ids:
        r = requests.get(URL + f"/api/data/v9.2/workflows({fid})?$select=name,statecode", headers=H)
        if r.status_code == 200 and r.json().get('statecode') == 0:
            disabled += 1
    if not check("Loop-prone cloud flows are disabled (statecode=0)", disabled == len(flow_ids),
                 f"{disabled}/{len(flow_ids)} off"):
        failures += 1

    print()
    if failures:
        print(f"❌ {failures} check(s) failed.")
        return 1
    print("✅ All checks passed — Ep 10 demo data is recording-ready.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
