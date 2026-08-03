"""
trigger_red_health.py  --  Ep 10 E2E trigger: write lc_statusupdate health=RED
                            to Dataverse, then wait for Fabric Link replication.

Demonstrates the two-plane architecture:
  Studio agent writes lc_statusupdate (health=RED)
  → Fabric Link replicates to OneLake (~46s median latency measured)
  → Lakehouse SQL endpoint makes it queryable by the Fabric Data Agent
  → Launch Analyst agent detects it and escalates to Teams

Usage:
    python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply
    python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --dry-run
    python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --wait 60
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import scripts.auth as auth  # noqa: E402


# ---------------------------------------------------------------------------
# lc_health option set values (Dataverse env: eppcdemo1fno)
# ---------------------------------------------------------------------------
HEALTH_GREEN = 10600601
HEALTH_AMBER = 10600602
HEALTH_RED   = 10600603

# ---------------------------------------------------------------------------
# Demo payload  (title + summary chosen to show vendor context in KQL join)
# ---------------------------------------------------------------------------
DEMO_UPDATES = [
    {
        "lc_title": "Localization vendor SLA breach - RED",
        "lc_summary": (
            "Acme Translations (V0001) missed the Q3 strings deadline by 3 days. "
            "61% on-time rate with 2 open disputes. Launch date impact: HIGH."
        ),
        "lc_health": HEALTH_RED,
    },
    {
        "lc_title": "Logistics partner ship-window blocked - RED",
        "lc_summary": (
            "SwiftLogix (V0003) unable to confirm freight window due to carrier capacity. "
            "74% on-time, 1 open dispute. Physical launch material at risk."
        ),
        "lc_health": HEALTH_RED,
    },
]


# ---------------------------------------------------------------------------
# Dataverse helpers
# ---------------------------------------------------------------------------

def _get_first_launch_id(base: str, tok: str) -> str | None:
    """Return the first lc_launch ID in the environment."""
    url = base + "/api/data/v9.2/lc_launchs?$select=lc_launchid&$top=1"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0", "OData-Version": "4.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.load(resp).get("value", [])
    return rows[0]["lc_launchid"] if rows else None


def write_status_update(base: str, tok: str, payload: dict) -> str:
    """POST an lc_statusupdate and return the new record ID."""
    url = base + "/api/data/v9.2/lc_statusupdates"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0", "OData-Version": "4.0",
        "Prefer": "return=representation",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    return result.get("lc_statusupdateid", "")


def delete_status_update(base: str, tok: str, record_id: str) -> None:
    """DELETE an lc_statusupdate by ID (cleanup after demo)."""
    url = base + f"/api/data/v9.2/lc_statusupdates({record_id})"
    req = urllib.request.Request(url, method="DELETE", headers={
        "Authorization": f"Bearer {tok}",
        "OData-MaxVersion": "4.0", "OData-Version": "4.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        pass  # 204 No Content on success


# ---------------------------------------------------------------------------
# KQL watch  (ARCHIVED: Eventhouse removed in favour of Lakehouse SQL endpoint)
# Kept for reference; --watch flag now uses a simple timed wait instead.
# ---------------------------------------------------------------------------

def _timed_wait(seconds: int) -> None:
    """Simple countdown while Fabric Link replicates."""
    print(f"\nWaiting {seconds}s for Fabric Link replication (~46s median)...")
    for remaining in range(seconds, 0, -10):
        print(f"  {remaining}s remaining...")
        time.sleep(min(10, remaining))
    print("  Done. Records should now be visible in the Lakehouse SQL endpoint.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Ep 10 E2E trigger: write RED health updates.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--wait", type=int, default=0,
                        help="After writing, wait N seconds for Fabric Link replication (0 = skip)")
    parser.add_argument("--cleanup", action="store_true",
                        help="Delete written records after KQL watch (demo cleanup)")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        return 1

    dry_run = not args.apply

    auth.load_env("ep-10-dataverse-fabriciq")
    base = os.environ["DATAVERSE_URL"].rstrip("/")

    print(f"Dataverse: {base}")
    print(f"Mode     : {'DRY RUN' if dry_run else 'APPLY'}")
    print()

    if dry_run:
        print("Would write the following lc_statusupdate records:")
        for u in DEMO_UPDATES:
            print(f"  [{u['lc_health']}] {u['lc_title']}")
        print("  (health=3 = RED)")
        return 0

    tok = auth.get_token("ep-10-dataverse-fabriciq")

    # Get a launch ID to associate updates with
    launch_id = _get_first_launch_id(base, tok)
    if launch_id:
        print(f"Using launch ID: {launch_id}")
    else:
        print("No launch found - writing status updates without launch association")

    written_ids = []
    for update in DEMO_UPDATES:
        payload = {
            "lc_title": update["lc_title"],
            "lc_summary": update["lc_summary"],
            "lc_health": update["lc_health"],
        }
        if launch_id:
            payload["lc_launchid@odata.bind"] = f"/lc_launchs({launch_id})"

        print(f"Writing: {update['lc_title'][:60]}...")
        try:
            record_id = write_status_update(base, tok, payload)
            written_ids.append(record_id)
            print(f"  → lc_statusupdateid: {record_id}")
        except Exception as e:
            print(f"  ERR: {e}")

    if not written_ids:
        print("No records written.")
        return 1

    print(f"\nWrote {len(written_ids)} RED health status update(s) to Dataverse.")
    print("These will replicate to the Fabric Lakehouse via Fabric Link (~46s median).")

    if args.wait > 0:
        _timed_wait(args.wait)

    if args.cleanup and written_ids:
        print("\nCleaning up demo records...")
        tok2 = auth.get_token("ep-10-dataverse-fabriciq")
        for record_id in written_ids:
            try:
                delete_status_update(base, tok2, record_id)
                print(f"  Deleted {record_id}")
            except Exception as e:
                print(f"  Delete {record_id} failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
