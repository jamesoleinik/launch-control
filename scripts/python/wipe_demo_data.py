"""Wipe demo data from staging + unified tables for a clean re-ingest.

Deletes every row from:
    lc_task, lc_milestone     (unified)
    lc_trackera..lc_trackere  (staging)
    lc_sourcefile, lc_importrun (provenance)

Schema (tables, columns, choices) is preserved. Only rows are removed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

# Order matters: unified before staging (provenance lookup), provenance last.
WIPE_ORDER = [
    ("lc_task", "lc_taskid"),
    ("lc_milestone", "lc_milestoneid"),
    ("lc_trackera", "lc_trackeraid"),
    ("lc_trackerb", "lc_trackerbid"),
    ("lc_trackerc", "lc_trackercid"),
    ("lc_trackerd", "lc_trackerdid"),
    ("lc_trackere", "lc_trackereid"),
    ("lc_sourcefile", "lc_sourcefileid"),
    ("lc_importrun", "lc_importrunid"),
]


def main() -> int:
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")

    with DataverseClient(env_url, get_credential()) as client:
        for table, pk in WIPE_ORDER:
            rows = client.query_sql(f"SELECT {pk} FROM {table}")
            ids = [r[pk] for r in rows if r.get(pk)]
            print(f"  {table}: {len(ids)} rows", end="", flush=True)
            if not ids:
                print(" (skip)")
                continue
            client.delete(table, ids, use_bulk_delete=True)
            print(" -> deleted")

    print("\nWipe complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
