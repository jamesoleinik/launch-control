"""Prove the three lc_task rule plugins fire from raw Web API PATCHes.

Test target: 'Performance benchmark for widget load' (status=NotStarted,
blockerreason=null). After each scenario we read back the row and assert
the expected outcome; final state is restored at the end.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from auth import get_token, load_env

STATUS_NAMES = {
    10600301: "NotStarted",
    10600302: "InProgress",
    10600303: "Blocked",
    10600304: "Done",
}

load_env()
base = os.environ["DATAVERSE_URL"].rstrip("/")
tok = get_token()


def api(method, path, body=None):
    url = f"{base}/api/data/v9.2/{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {tok}")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if method == "PATCH":
        req.add_header("If-Match", "*")
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read().decode("utf-8")
            return r.status, (json.loads(txt) if txt else None), None
    except urllib.error.HTTPError as e:
        return e.code, None, e.read().decode("utf-8")


def get_task(task_id):
    _, payload, _ = api("GET",
        f"lc_tasks({task_id})?$select=lc_title,lc_taskstatus,lc_blockerreason")
    return payload


def find_task(title):
    flt = urllib.parse.quote(f"lc_title eq '{title}'", safe="")
    _, payload, _ = api("GET",
        f"lc_tasks?$filter={flt}&$select=lc_taskid,lc_title,lc_taskstatus,lc_blockerreason")
    return payload["value"][0]


def reset(task_id):
    api("PATCH", f"lc_tasks({task_id})",
        {"lc_blockerreason": None, "lc_taskstatus": 10600301})  # NotStarted


def show(label, row):
    print(f"    {label:<14} status={STATUS_NAMES.get(row['lc_taskstatus'])!s:<11} "
          f"blockerreason={row['lc_blockerreason']!r}")


def assert_eq(name, actual, expected):
    ok = actual == expected
    sym = "[OK]" if ok else "[FAIL]"
    print(f"    {sym} {name}: got {actual!r}, expected {expected!r}")
    return ok


task = find_task("Performance benchmark for widget load")
tid = task["lc_taskid"]
print(f"Test task: {task['lc_title']} ({tid})")
reset(tid)
print(f"Initial state after reset:")
show("BEFORE", get_task(tid))

results = []

# -------------------------------------------------------------------
# RULE 1 — Set blockerreason -> status auto-flips to Blocked
# -------------------------------------------------------------------
print("\n[Rule 1] PATCH { lc_blockerreason: 'Waiting on auth team' }")
code, _, err = api("PATCH", f"lc_tasks({tid})",
                   {"lc_blockerreason": "Waiting on auth team"})
print(f"  HTTP {code}{(' err=' + err[:200]) if err else ''}")
row = get_task(tid)
show("AFTER", row)
ok = assert_eq("Rule 1 forces status=Blocked",
               STATUS_NAMES[row["lc_taskstatus"]], "Blocked")
ok &= assert_eq("Rule 1 preserves blockerreason",
                row["lc_blockerreason"], "Waiting on auth team")
results.append(("Rule 1 (auto-Block on reason set)", ok))

# -------------------------------------------------------------------
# RULE 3 — Trying to mark Done while blockerreason set must FAIL
#   (run before Rule 2 because we still have the blocker set)
# -------------------------------------------------------------------
print("\n[Rule 3] PATCH { lc_taskstatus: Done } while blockerreason still set")
code, _, err = api("PATCH", f"lc_tasks({tid})", {"lc_taskstatus": 10600304})
err_short = (err or "").split('"message":"', 1)[-1].split('"', 1)[0] if err else ""
print(f"  HTTP {code}  message: {err_short[:200]}")
row = get_task(tid)
show("AFTER", row)
ok = assert_eq("Rule 3 HTTP status is 4xx", code >= 400, True)
ok &= assert_eq("Rule 3 error mentions 'blocker'",
                "blocker" in (err or "").lower(), True)
ok &= assert_eq("Row state unchanged: status still Blocked",
                STATUS_NAMES[row["lc_taskstatus"]], "Blocked")
ok &= assert_eq("Row state unchanged: blockerreason intact",
                row["lc_blockerreason"], "Waiting on auth team")
results.append(("Rule 3 (refuse Done with blocker)", ok))

# -------------------------------------------------------------------
# RULE 2 — Clear blockerreason on Blocked task -> status reverts to InProgress
# -------------------------------------------------------------------
print("\n[Rule 2] PATCH { lc_blockerreason: null } on Blocked task")
code, _, err = api("PATCH", f"lc_tasks({tid})", {"lc_blockerreason": None})
print(f"  HTTP {code}{(' err=' + err[:200]) if err else ''}")
row = get_task(tid)
show("AFTER", row)
ok = assert_eq("Rule 2 reverts status -> InProgress",
               STATUS_NAMES[row["lc_taskstatus"]], "InProgress")
ok &= assert_eq("Rule 2 clears blockerreason",
                row["lc_blockerreason"], None)
results.append(("Rule 2 (auto-InProgress on reason clear)", ok))

# Negative check for Rule 2: clearing blocker on a non-Blocked task should NOT
# touch status. Set status to NotStarted with no blocker, then PATCH a no-op
# clear of blocker; status must stay NotStarted.
print("\n[Rule 2 — negative] Clear blocker on NotStarted task; status must NOT change")
api("PATCH", f"lc_tasks({tid})",
    {"lc_blockerreason": None, "lc_taskstatus": 10600301})
api("PATCH", f"lc_tasks({tid})", {"lc_blockerreason": None})
row = get_task(tid)
show("AFTER", row)
ok = assert_eq("Status stays NotStarted (no Blocked PreImage -> no-op)",
               STATUS_NAMES[row["lc_taskstatus"]], "NotStarted")
results.append(("Rule 2 negative (no false revert)", ok))

# Cleanup
reset(tid)
print("\nFinal state restored:")
show("RESET", get_task(tid))

# Summary
print("\n=== RESULTS ===")
for name, ok in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print()
all_pass = all(ok for _, ok in results)
sys.exit(0 if all_pass else 1)
