"""Teardown LaunchControl: delete all lc_ tables, then solution, then publisher.

Order matters:
1. Delete lookups that cross tables (Dataverse complains if you delete a target
   table while a lookup still points at it). We do this by deleting tables in
   reverse dependency order.
2. Delete the solution record.
3. Delete the publisher record.

Idempotent: missing items are skipped.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from scripts._resilient import is_duplicate, short_error
from PowerPlatform.Dataverse.client import DataverseClient

PREFIX = "lc"

# Reverse dependency order: leaf tables (with lookups pointing at others) first.
TABLES_IN_DELETE_ORDER = [
    f"{PREFIX}_statusupdate",
    f"{PREFIX}_task",
    f"{PREFIX}_milestone",
    f"{PREFIX}_launch",
    f"{PREFIX}_teammember",
    f"{PREFIX}_stg_tracker_a",
    f"{PREFIX}_stg_tracker_b",
    f"{PREFIX}_stg_tracker_c",
    f"{PREFIX}_stg_tracker_d",
    f"{PREFIX}_stg_tracker_e",
]


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")

    with DataverseClient(env_url, get_credential()) as client:
        print("Deleting tables (serialized)...")
        for table in TABLES_IN_DELETE_ORDER:
            info = client.tables.get(table)
            if not info:
                print(f"  {table}: not present, skip")
                continue
            try:
                client.tables.delete(table)
                print(f"  Deleted: {table}")
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR deleting {table}: {short_error(e)}")

        # --- Solution ---
        print("\nDeleting solution 'LaunchControl'...")
        pages = client.records.get(
            "solution",
            filter="uniquename eq 'LaunchControl'",
            select=["solutionid"],
            top=1,
        )
        sol = next((s for page in pages for s in page), None)
        if sol:
            try:
                client.records.delete("solution", sol["solutionid"])
                print("  Deleted solution.")
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR deleting solution: {short_error(e)}")
        else:
            print("  Solution not present, skip")

        # --- Publisher ---
        print("\nDeleting publisher 'LaunchControl'...")
        pages = client.records.get(
            "publisher",
            filter="uniquename eq 'LaunchControl' or uniquename eq 'launchcontrol'",
            select=["publisherid", "uniquename"],
            top=5,
        )
        pubs = [p for page in pages for p in page]
        for pub in pubs:
            try:
                client.records.delete("publisher", pub["publisherid"])
                print(f"  Deleted publisher: {pub['uniquename']}")
            except Exception as e:  # noqa: BLE001
                print(f"  ERROR deleting publisher {pub['uniquename']}: {short_error(e)}")
        if not pubs:
            print("  Publisher not present, skip")

        print("\n=== Teardown complete ===")


if __name__ == "__main__":
    main()
