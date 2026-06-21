"""Episode 8 — smoke-test: run the same reads through each persona by switching
the `MSCRMCallerID` impersonation header on one HTTP client.

Proves both security axes at once:
  * row-level  — `lc_task` count differs by role depth (Member User-depth sees
    only its own; Owner/Viewer see all at BU depth).
  * column-level — `lc_task.lc_blockerreason` and `lc_launch.lc_risksummary`
    are withheld (omitted) for principals outside the field-security profile,
    cleartext for the blocker column inside it, and masked for the risk column
    (cleartext only on an `?UnMaskedData=true` read backed by `canreadunmasked`).

Read-only. Requires the calling identity to hold `prvActOnBehalfOfAnotherUser`
(System Administrator does). Personas are resolved by domain name.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from auth import get_credential  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))
URL = os.environ["DATAVERSE_URL"].rstrip("/")
API = URL + "/api/data/v9.2"
TOK = get_credential().get_token(URL + "/.default").token
BASE = {"Authorization": f"Bearer {TOK}", "Accept": "application/json",
        "OData-MaxVersion": "4.0", "OData-Version": "4.0"}

PERSONAS = [
    ("Member (Walt)", "demoA365user130@agent365003.onmicrosoft.com"),
    ("Owner (Vivian)", "vivsun@agent365003.onmicrosoft.com"),
    ("Viewer (Rick)", "rbrighenti@agent365003.onmicrosoft.com"),
]


def g(path, caller=None, unmask=False):
    h = dict(BASE)
    if caller:
        h["MSCRMCallerID"] = caller
    if unmask:
        sep = "&" if "?" in path else "?"
        path = path + sep + "UnMaskedData=true"
    r = requests.get(API + path, headers=h)
    return r.status_code, (r.json() if r.text else {})


def col(row, name):
    """Return a printable cell: the value, or <omitted> if the key is absent."""
    if row is None:
        return "<no row>"
    return row.get(name, "<omitted>")


def main() -> int:
    print(f"Env: {URL}\n")

    users = requests.get(
        API + "/systemusers?$select=systemuserid,domainname,fullname&$top=300",
        headers=BASE).json()["value"]
    by_domain = {u["domainname"]: u for u in users}

    launch = requests.get(API + "/lc_launchs?$select=lc_launchid,lc_name",
                          headers=BASE).json()["value"][0]
    lid = launch["lc_launchid"]
    # Pick a blocked task to read the secured column from.
    blocked = requests.get(
        API + "/lc_tasks?$select=lc_taskid,lc_title&$filter=lc_isblocked eq true&$top=1",
        headers=BASE).json()["value"]
    tid = blocked[0]["lc_taskid"] if blocked else None

    print("=== Row-level: lc_task count per persona ===\n")
    print(f"{'Persona':18s} {'visible lc_task':>15s}")
    print("-" * 36)
    for label, domain in PERSONAS:
        uid = by_domain[domain]["systemuserid"]
        sc, j = g("/lc_tasks?$select=lc_taskid", caller=uid)
        n = len(j.get("value", [])) if sc == 200 else f"HTTP {sc}"
        print(f"{label:18s} {str(n):>15s}")

    print("\n=== Column-level: secured fields per persona ===\n")
    print(f"{'Persona':18s} {'blockerreason':28s} {'risksummary (plain)':24s} {'risksummary (unmasked)':24s}")
    print("-" * 98)
    for label, domain in PERSONAS:
        uid = by_domain[domain]["systemuserid"]
        br = "<no task>"
        if tid:
            sc, j = g(f"/lc_tasks({tid})?$select=lc_title,lc_blockerreason", caller=uid)
            br = col(j if sc == 200 else None, "lc_blockerreason")
        sc, j = g(f"/lc_launchs({lid})?$select=lc_name,lc_risksummary", caller=uid)
        rs = col(j if sc == 200 else None, "lc_risksummary")
        sc, j2 = g(f"/lc_launchs({lid})?$select=lc_name,lc_risksummary", caller=uid, unmask=True)
        rsu = col(j2 if sc == 200 else None, "lc_risksummary")
        print(f"{label:18s} {str(br)[:26]:28s} {str(rs)[:22]:24s} {str(rsu)[:22]:24s}")

    print("\nLegend: <omitted> = column withheld (caller outside the field-security profile).")
    print("Member is outside 'lc Sensitive Readers'; Owner is inside it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
