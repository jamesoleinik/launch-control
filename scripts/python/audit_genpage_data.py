"""Inspect Q3 Widget Launch task distribution to understand what the gen page sees."""
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_token, load_env  # type: ignore

import requests

load_env()
ORG = os.environ["DATAVERSE_URL"].rstrip("/")
H = {"Authorization": f"Bearer {get_token()}", "Accept": "application/json"}

r = requests.get(
    f"{ORG}/api/data/v9.2/EntityDefinitions(LogicalName='lc_launch')?$select=EntitySetName",
    headers=H, timeout=30,
)
launch_set = r.json().get("EntitySetName") if r.ok else "lc_launchs"
ms_set = requests.get(f"{ORG}/api/data/v9.2/EntityDefinitions(LogicalName='lc_milestone')?$select=EntitySetName", headers=H, timeout=30).json().get("EntitySetName")
tk_set = requests.get(f"{ORG}/api/data/v9.2/EntityDefinitions(LogicalName='lc_task')?$select=EntitySetName", headers=H, timeout=30).json().get("EntitySetName")
su_set = requests.get(f"{ORG}/api/data/v9.2/EntityDefinitions(LogicalName='lc_statusupdate')?$select=EntitySetName", headers=H, timeout=30).json().get("EntitySetName")
print(f"sets: launch={launch_set} ms={ms_set} tk={tk_set} su={su_set}")

r = requests.get(
    f"{ORG}/api/data/v9.2/{launch_set}?$select=lc_launchid,lc_name&$filter=statecode eq 0",
    headers=H, timeout=30,
)
r.raise_for_status()
launches = r.json()["value"]
q3 = next((l for l in launches if "q3" in l["lc_name"].lower()), launches[0] if launches else None)
if not q3:
    print("NO LAUNCHES")
    sys.exit(1)

print(f"=== {q3['lc_name']} (id={q3['lc_launchid']}) ===\n")

# Milestones
ms = requests.get(
    f"{ORG}/api/data/v9.2/{ms_set}?$select=lc_milestoneid,lc_name,lc_milestonestatus&$filter=_lc_launchid_value eq {q3['lc_launchid']} and statecode eq 0",
    headers=H, timeout=30,
).json()["value"]
print(f"Milestones: {len(ms)}")
ms_status_map = {10600010:"NotStarted",10600011:"InProgress",10600012:"Complete",10600013:"AtRisk",10600014:"Blocked"}
for m in ms:
    print(f"  - {m['lc_name']} [{ms_status_map.get(m['lc_milestonestatus'], '?')}]")

ms_ids = {m["lc_milestoneid"].lower() for m in ms}

# Tasks
tk = requests.get(
    f"{ORG}/api/data/v9.2/{tk_set}?$select=lc_taskid,lc_title,lc_taskstatus,lc_isblocked,lc_blockerreason,_lc_milestoneid_value,_lc_assignedtoid_value&$filter=statecode eq 0&$top=500",
    headers=H, timeout=30,
).json()["value"]

q3_tasks = [t for t in tk if t.get("_lc_milestoneid_value") and t["_lc_milestoneid_value"].lower() in ms_ids]
print(f"\nTasks total (active): {len(tk)}")
print(f"Tasks linked to {q3['lc_name']} milestones: {len(q3_tasks)}")

ts_map = {10600020:"NotStarted",10600021:"InProgress",10600022:"Done",10600023:"Blocked"}
status_counts = Counter(ts_map.get(t["lc_taskstatus"], "Unknown") for t in q3_tasks)
print("\nKanban distribution (Q3 tasks):")
for k in ["NotStarted","InProgress","Blocked","Done","Unknown"]:
    print(f"  {k:12s}: {status_counts.get(k, 0)}")

# Owner / blockerreason coverage
with_owner = sum(1 for t in q3_tasks if t.get("_lc_assignedtoid_value"))
blocked = [t for t in q3_tasks if ts_map.get(t["lc_taskstatus"]) == "Blocked"]
blocked_with_reason = sum(1 for t in blocked if t.get("lc_blockerreason"))
print(f"\nQ3 tasks with owner:         {with_owner}/{len(q3_tasks)}")
print(f"Q3 Blocked tasks with reason: {blocked_with_reason}/{len(blocked)}")

# Status updates
su = requests.get(
    f"{ORG}/api/data/v9.2/{su_set}?$select=lc_title,lc_updatedon&$filter=_lc_launchid_value eq {q3['lc_launchid']} and statecode eq 0",
    headers=H, timeout=30,
).json()["value"]
print(f"\nStatus updates for Q3: {len(su)}")

# Acceptance against the new todo
print("\n=== Acceptance check (>=3 per kanban column, owner+blocker coverage, >=8 status updates) ===")
ok = True
for k in ["NotStarted","InProgress","Blocked","Done"]:
    cnt = status_counts.get(k, 0)
    mark = "OK " if cnt >= 3 else "FAIL"
    if cnt < 3: ok = False
    print(f"  [{mark}] {k:12s}: {cnt} (need >=3)")
mark = "OK " if with_owner == len(q3_tasks) else "FAIL"
if with_owner != len(q3_tasks): ok = False
print(f"  [{mark}] Every task has owner: {with_owner}/{len(q3_tasks)}")
mark = "OK " if blocked_with_reason == len(blocked) else "FAIL"
if blocked_with_reason != len(blocked): ok = False
print(f"  [{mark}] Every Blocked has reason: {blocked_with_reason}/{len(blocked)}")
mark = "OK " if len(su) >= 8 else "FAIL"
if len(su) < 8: ok = False
print(f"  [{mark}] Status updates: {len(su)} (need >=8)")
print(f"\nOverall: {'PASS' if ok else 'FAIL — needs more seeding'}")
