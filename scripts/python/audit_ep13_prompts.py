"""Episode 13 prompt preflight: verify the data shape Dataverse Intelligence will need
to answer the three demo prompts (and the backup) on recording day.

Prompts vouched for:
  P1 (read):       "What's the status of the Q3 Widget Launch?"
  P2 (traversal):  "Who's assigned to the most tasks for the Q3 Widget Launch?"
  P3 (filter):     "Show me the blocked tasks for the Q3 Widget Launch and why."
  PB (backup):     "Summarize the risks for the Q3 Widget Launch."

This script does NOT verify Copilot grounding (toggle + indexing is a separate human
checklist). It only confirms the underlying Dataverse rows exist with the right shape.

Run: python scripts/python/audit_ep11_prompts.py
"""
import os, sys
import requests
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv
from auth import get_credential

load_dotenv(os.path.join(ROOT, '.env'))
URL = os.environ['DATAVERSE_URL']
TOK = get_credential().get_token(URL + '/.default').token
H = {'Authorization': 'Bearer ' + TOK, 'Accept': 'application/json',
     'Prefer': 'odata.include-annotations="*"'}

# Q3 Widget Launch is the demo subject
LAUNCH_NAME = os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch')

# Option set values (lc_taskstatus and lc_milestonestatus)
TASK_BLOCKED = 10600023
MS_AT_RISK_LABELS = {'AtRisk', 'Blocked'}  # both signal "needs attention"


def fetch(path):
    out, full = [], URL + path
    while full:
        r = requests.get(full, headers=H)
        r.raise_for_status()
        j = r.json()
        out.extend(j.get('value', []))
        full = j.get('@odata.nextLink')
    return out


def check(name, ok, detail=''):
    icon = 'PASS' if ok else 'FAIL'
    print(f"  [{icon}]  {name}{(' -- ' + detail) if detail else ''}")
    return ok


def main():
    print(f"Episode 13 prompt preflight (launch: {LAUNCH_NAME!r})\n")
    failures = 0

    # P1: launch row exists with name + status + description + target date
    safe_name = LAUNCH_NAME.replace("'", "''")
    launches = fetch(
        "/api/data/v9.2/lc_launchs?$select=lc_launchid,lc_name,lc_launchstatus,"
        "lc_targetdate,lc_description,cr88d_risksummary"
        f"&$filter=lc_name eq '{safe_name}'")
    if not check("P1: Launch row exists", len(launches) == 1, f"got {len(launches)}"):
        return 1
    L = launches[0]
    lid = L['lc_launchid']
    status = L.get('lc_launchstatus@OData.Community.Display.V1.FormattedValue')
    target = L.get('lc_targetdate@OData.Community.Display.V1.FormattedValue')
    desc = (L.get('lc_description') or '').strip()
    if not check("P1: Launch has status", bool(status), f"status={status!r}"):
        failures += 1
    if not check("P1: Launch has target date", bool(target), f"target={target!r}"):
        failures += 1
    if not check("P1: Launch has description >= 40 chars", len(desc) >= 40,
                 f"len={len(desc)}"):
        failures += 1

    # P2: tasks under Q3 milestones, with assignedto resolving to TeamMember names
    ms = fetch("/api/data/v9.2/lc_milestones?$select=lc_milestoneid,lc_milestonestatus"
               f"&$filter=_lc_launchid_value eq {lid}")
    ms_ids = {m['lc_milestoneid'] for m in ms}
    if not check("P2: Q3 has >= 8 milestones", len(ms) >= 8, f"got {len(ms)}"):
        failures += 1

    tasks = fetch("/api/data/v9.2/lc_tasks?$select=lc_taskid,lc_title,lc_taskstatus,"
                  "lc_blockerreason,_lc_milestoneid_value,_lc_assignedtoid_value")
    q3_tasks = [t for t in tasks if t.get('_lc_milestoneid_value') in ms_ids]
    if not check("P2: Q3 tasks >= 30", len(q3_tasks) >= 30, f"got {len(q3_tasks)}"):
        failures += 1
    assignees = Counter(
        t.get('_lc_assignedtoid_value@OData.Community.Display.V1.FormattedValue')
        for t in q3_tasks if t.get('_lc_assignedtoid_value'))
    distinct = len([n for n in assignees if n])
    if not check("P2: distinct task assignees >= 4", distinct >= 4,
                 f"distinct={distinct}, top={assignees.most_common(3)}"):
        failures += 1
    top = assignees.most_common(1)
    if not check("P2: top assignee owns >= 5 Q3 tasks",
                 bool(top) and top[0][1] >= 5,
                 f"top={top}"):
        failures += 1

    # P3: blocked Q3 tasks each with non-empty reason
    blocked = [t for t in q3_tasks if t.get('lc_taskstatus') == TASK_BLOCKED]
    if not check("P3: blocked Q3 tasks >= 4", len(blocked) >= 4, f"got {len(blocked)}"):
        failures += 1
    blocked_with_reason = [t for t in blocked if (t.get('lc_blockerreason') or '').strip()]
    if not check("P3: every blocked task has a non-empty reason",
                 len(blocked_with_reason) == len(blocked),
                 f"{len(blocked_with_reason)}/{len(blocked)}"):
        failures += 1

    # PB: backup — risk summary populated on launch row OR >= 2 milestones AtRisk/Blocked
    risk_text = (L.get('cr88d_risksummary') or '').strip()
    pb_a = check("PB: launch.cr88d_risksummary populated >= 80 chars",
                 len(risk_text) >= 80, f"len={len(risk_text)}")
    at_risk = [m for m in ms
               if m.get('lc_milestonestatus@OData.Community.Display.V1.FormattedValue')
               in MS_AT_RISK_LABELS]
    pb_b = check("PB: milestones in AtRisk/Blocked >= 2", len(at_risk) >= 2,
                 f"got {len(at_risk)}")
    if not (pb_a or pb_b):
        failures += 1
        print("  [FAIL]  PB: backup-prompt path not viable (need either populated risk "
              "summary OR >=2 at-risk milestones)")

    print()
    if failures == 0:
        print("ALL GREEN -- prompts will have data to ground against.")
        print()
        print("REMEMBER: this script verifies Dataverse rows. It does NOT verify the")
        print("Dataverse Intelligence toggle is on or that indexing has caught up.")
        print("Run the smoke prompt manually before recording.")
        return 0
    print(f"{failures} FAILURE(S) -- fix the data before recording.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
