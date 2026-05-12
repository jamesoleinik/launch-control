"""Quick row-count check on the 5 staging tables (no writes).

Reads $count from each lc_TrackerX entity set and prints a one-line summary
so you can confirm data actually landed.
"""

from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env  # noqa: E402

TABLES = ["lc_trackera", "lc_trackerb", "lc_trackerc", "lc_trackerd", "lc_trackere"]


def main() -> int:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-Version": "4.0",
        "Prefer": 'odata.include-annotations="*"',
    }

    print(f"\nRow counts in {url}\n")
    total = 0
    for t in TABLES:
        # entity set is logical + 's' for lc_ tables (matches seed_data._entity_set)
        r = requests.get(
            f"{url}/api/data/v9.2/{t}s/$count",
            headers={**headers, "Accept": "text/plain"},
            timeout=30,
        )
        if not r.ok:
            print(f"  {t:<14}  HTTP {r.status_code}")
            continue
        n = int(r.content.decode("utf-8-sig").strip())
        total += n
        print(f"  {t:<14}  {n:>4} row(s)")

    # Also peek at lc_importrun
    r = requests.get(
        f"{url}/api/data/v9.2/lc_importruns?$select=lc_name,lc_status,lc_recordsprocessed"
        "&$orderby=createdon desc&$top=3",
        headers=headers, timeout=30,
    )
    if r.ok:
        runs = r.json().get("value", [])
        print(f"\nLatest lc_ImportRuns:")
        for run in runs:
            status = run.get("lc_status@OData.Community.Display.V1.FormattedValue") or run.get("lc_status")
            print(f"  - {run.get('lc_name')}  status={status}  records={run.get('lc_recordsprocessed')}")

    print(f"\nTotal staging rows: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
