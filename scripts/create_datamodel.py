"""Episode 1: Create the Launch Control data model in Dataverse.

Creates:
- Publisher and Solution
- Tables: Launches, Milestones, Tasks, TeamMembers, StatusUpdates
- Relationships between tables
- Choice columns for status fields
"""

import os
import sys
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from scripts._resilient import attempt_many, is_duplicate
from PowerPlatform.Dataverse.client import DataverseClient


class LaunchStatus(Enum):
    Planning = 10600001
    InProgress = 10600002
    ReadyForLaunch = 10600003
    Launched = 10600004
    OnHold = 10600005


class MilestoneStatus(Enum):
    NotStarted = 10600010
    InProgress = 10600011
    Complete = 10600012
    AtRisk = 10600013
    Blocked = 10600014


class TaskStatus(Enum):
    NotStarted = 10600020
    InProgress = 10600021
    Done = 10600022
    Blocked = 10600023


def _is_duplicate(e):
    """Check if an exception indicates a duplicate record."""
    return is_duplicate(e)


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    prefix = "lc"
    solution_name = "LaunchControl"

    with DataverseClient(env_url, credential) as client:

        # --- Publisher ---
        print("Creating publisher...")
        try:
            client.records.create("publisher", {
                "uniquename": "launchcontrol",
                "friendlyname": "Launch Control",
                "customizationprefix": prefix,
                "customizationoptionvalueprefix": 10600,
                "description": "Publisher for the Launch Control demo project",
            })
            print("  Publisher created: launchcontrol")
        except Exception as e:
            if _is_duplicate(e):
                print("  Publisher already exists, skipping.")
            else:
                raise

        # --- Solution ---
        print("Creating solution...")
        pages = client.records.get(
            "publisher",
            filter="uniquename eq 'launchcontrol'",
            select=["publisherid"],
            top=1,
        )
        publisher_id = None
        for page in pages:
            for rec in page:
                publisher_id = rec["publisherid"]
        if not publisher_id:
            print("ERROR: Could not find publisher.")
            return

        try:
            client.records.create("solution", {
                "uniquename": solution_name,
                "friendlyname": "Launch Control",
                "version": "1.0.0.0",
                "description": "Product Launch Coordinator - Launch Control LinkedIn series",
                "publisherid@odata.bind": f"/publishers({publisher_id})",
            })
            print(f"  Solution created: {solution_name}")
        except Exception as e:
            if _is_duplicate(e):
                print("  Solution already exists, skipping.")
            else:
                raise

        # --- Tables ---
        # SDK signature: client.tables.create(table_schema_name, columns_dict, solution=, primary_column=)
        print("\nCreating tables...")

        tables = [
            (f"{prefix}_Launch", {
                f"{prefix}_TargetDate": "datetime",
                f"{prefix}_Description": "memo",
                f"{prefix}_LaunchStatus": LaunchStatus,
            }, f"{prefix}_Name"),
            (f"{prefix}_Milestone", {
                f"{prefix}_DueDate": "datetime",
                f"{prefix}_SortOrder": "integer",
                f"{prefix}_MilestoneStatus": MilestoneStatus,
            }, f"{prefix}_Name"),
            (f"{prefix}_Task", {
                f"{prefix}_DueDate": "datetime",
                f"{prefix}_Description": "memo",
                f"{prefix}_IsBlocked": "boolean",
                f"{prefix}_BlockerReason": "string",
                f"{prefix}_TaskStatus": TaskStatus,
            }, f"{prefix}_Title"),
            (f"{prefix}_TeamMember", {
                f"{prefix}_Email": "string",
                f"{prefix}_Role": "string",
            }, f"{prefix}_Name"),
            (f"{prefix}_StatusUpdate", {
                f"{prefix}_Body": "memo",
                f"{prefix}_UpdatedOn": "datetime",
            }, f"{prefix}_Title"),
        ]

        print(f"Creating {len(tables)} tables in parallel...")
        attempt_many(
            [
                (
                    schema,
                    lambda s=schema, c=cols, p=primary: client.tables.create(
                        s, c, solution=solution_name, primary_column=p,
                    ),
                )
                for schema, cols, primary in tables
            ],
            workers=min(5, len(tables)),
        )

        # --- Relationships (Lookups) ---
        # Lookups touching the same target entity contend on Dataverse's
        # EntityCustomization lock; serial is more reliable than parallel here.
        print("\nCreating relationships (serialized)...")
        lookups = [
            (f"{prefix}_Milestone", f"{prefix}_LaunchId", f"{prefix}_Launch", "Launch"),
            (f"{prefix}_Task", f"{prefix}_MilestoneId", f"{prefix}_Milestone", "Milestone"),
            (f"{prefix}_Task", f"{prefix}_AssignedToId", f"{prefix}_TeamMember", "Assigned To"),
            (f"{prefix}_StatusUpdate", f"{prefix}_LaunchId", f"{prefix}_Launch", "Launch"),
            (f"{prefix}_TeamMember", f"{prefix}_LaunchId", f"{prefix}_Launch", "Launch"),
        ]

        attempt_many(
            [
                (
                    f"{ref_table} -> {target_table} ({display})",
                    lambda r=ref_table, n=lookup_name, t=target_table, d=display: client.tables.create_lookup_field(
                        r, n, t, display_name=d, solution=solution_name,
                    ),
                )
                for ref_table, lookup_name, target_table, display in lookups
            ],
            workers=1,
        )

        print("\n=== Episode 1 data model complete! ===")
        print("Tables: Launch, Milestone, Task, TeamMember, StatusUpdate")
        print("Columns: status choices, dates, descriptions, blocker flags")
        print("Relationships: Launch->Milestones->Tasks->TeamMembers, StatusUpdates->Launch")


if __name__ == "__main__":
    main()
