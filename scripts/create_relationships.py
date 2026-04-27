"""Create lookup relationships between Launch Control tables.

Uses lowercase logical names as required by the SDK.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    prefix = "lc"
    solution_name = "LaunchControl"

    with DataverseClient(env_url, credential) as client:
        print("Creating relationships (using logical names)...")

        lookups = [
            ("lc_milestone", f"{prefix}_LaunchId", "lc_launch", "Launch"),
            ("lc_task", f"{prefix}_MilestoneId", "lc_milestone", "Milestone"),
            ("lc_task", f"{prefix}_AssignedToId", "lc_teammember", "Assigned To"),
            ("lc_statusupdate", f"{prefix}_LaunchId", "lc_launch", "Launch"),
            ("lc_teammember", f"{prefix}_LaunchId", "lc_launch", "Launch"),
        ]

        for ref_table, lookup_name, target_table, display in lookups:
            try:
                result = client.tables.create_lookup_field(
                    ref_table,
                    lookup_name,
                    target_table,
                    display_name=display,
                    solution=solution_name,
                )
                print(f"  {ref_table} -> {target_table} ({display}) OK")
            except Exception as e:
                msg = str(e).lower()
                if any(x in msg for x in ["duplicate", "already exists", "matching key", "already being used"]):
                    print(f"  {ref_table} -> {target_table} already exists, skipping.")
                else:
                    print(f"  Error: {ref_table} -> {target_table}: {e}")

        print("\nDone! Relationships created.")


if __name__ == "__main__":
    main()
