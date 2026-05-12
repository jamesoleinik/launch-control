"""Quick verification that Episode 1 unified + staging tables exist in Dataverse.

Queries Dataverse metadata for the 12 expected lc_ tables and prints a
compact summary: table name, attribute count, ImportRun lookup present?

Used as the post-build sanity check. No writes.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import quote

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env  # noqa: E402


EXPECTED = [
    # unified
    ("lc_launch", False),
    ("lc_milestone", True),
    ("lc_task", True),
    ("lc_teammember", True),
    ("lc_statusupdate", True),
    # provenance
    ("lc_importrun", False),
    ("lc_sourcefile", True),
    # staging
    ("lc_trackera", True),
    ("lc_trackerb", True),
    ("lc_trackerc", True),
    ("lc_trackerd", True),
    ("lc_trackere", True),
]


def main() -> int:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-Version": "4.0",
    }

    print(f"\nVerifying schema in {url}\n")
    print(f"{'Table':<22} {'Attrs':>6}  {'ImportRun':>9}  {'Status'}")
    print("-" * 70)

    all_ok = True
    for logical, expect_lookup in EXPECTED:
        meta_url = (
            f"{url}/api/data/v9.2/EntityDefinitions(LogicalName='{logical}')"
            f"?$select=LogicalName&$expand=Attributes($select=LogicalName)"
        )
        r = requests.get(meta_url, headers=headers, timeout=30)
        if r.status_code == 404:
            print(f"{logical:<22} {'-':>6}  {'-':>9}  MISSING")
            all_ok = False
            continue
        if not r.ok:
            print(f"{logical:<22} {'?':>6}  {'?':>9}  HTTP {r.status_code}")
            all_ok = False
            continue
        data = r.json()
        attrs = [a["LogicalName"] for a in data.get("Attributes", [])]
        has_importrun = "lc_importrunid" in attrs
        status = "OK"
        if expect_lookup and not has_importrun:
            status = "MISSING lc_importrunid"
            all_ok = False
        print(
            f"{logical:<22} {len(attrs):>6}  "
            f"{('yes' if has_importrun else 'no'):>9}  {status}"
        )

    print("\nResult:", "ALL OK" if all_ok else "ISSUES FOUND")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
