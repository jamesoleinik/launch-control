"""Episode 8 — smoke-test: run the same reads through each persona by switching
the `MSCRMCallerID` impersonation header on one HTTP client.

Proves both security axes at once:
  * row-level: `lc_task` count differs by role depth (Member User-depth sees
    only its own; Owner/Viewer see all at BU depth).
  * column-level: the `lc_teammember` PII columns. `lc_email` is masked by a
    rule (redacted on a plain read; cleartext only on an `?UnMaskedData=true`
    read backed by `canreadunmasked`). `lc_fullname` is hidden by pure column
    security (omitted for principals outside the `lc Sensitive Readers` profile,
    cleartext inside it). The task and launch columns are not secured.

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

    # Pick a team-member row to read the secured PII columns from.
    tm = requests.get(
        API + "/lc_teammembers?$select=lc_teammemberid,lc_name&$top=1",
        headers=BASE).json()["value"]
    tmid = tm[0]["lc_teammemberid"] if tm else None

    print("=== Row-level: lc_task count per persona ===\n")
    print(f"{'Persona':18s} {'visible lc_task':>15s}")
    print("-" * 36)
    for label, domain in PERSONAS:
        uid = by_domain[domain]["systemuserid"]
        sc, j = g("/lc_tasks?$select=lc_taskid", caller=uid)
        n = len(j.get("value", [])) if sc == 200 else f"HTTP {sc}"
        print(f"{label:18s} {str(n):>15s}")

    print("\n=== Column-level: lc_teammember PII per persona ===\n")
    print(f"{'Persona':18s} {'email (plain)':24s} {'email (unmasked)':24s} {'fullname':24s}")
    print("-" * 92)
    for label, domain in PERSONAS:
        uid = by_domain[domain]["systemuserid"]
        email = unmasked = full = "<no row>"
        if tmid:
            sc, j = g(f"/lc_teammembers({tmid})?$select=lc_name,lc_email,lc_fullname", caller=uid)
            row = j if sc == 200 else None
            email = col(row, "lc_email")
            full = col(row, "lc_fullname")
            sc, j2 = g(f"/lc_teammembers({tmid})?$select=lc_name,lc_email", caller=uid, unmask=True)
            unmasked = col(j2 if sc == 200 else None, "lc_email")
        print(f"{label:18s} {str(email)[:22]:24s} {str(unmasked)[:22]:24s} {str(full)[:22]:24s}")

    print("\nLegend: <omitted> = column withheld (caller outside 'lc Sensitive Readers').")
    print("Member is outside the profile; Owner is inside it. lc_email is masked on a")
    print("plain read and clear under ?UnMaskedData=true; lc_fullname is omitted")
    print("outside the profile and clear inside it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
