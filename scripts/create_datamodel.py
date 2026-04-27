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
    msg = str(e).lower()
    return any(x in msg for x in ["duplicate", "already exists", "matching key", "already being used", "cannot be used again"])


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

        # 1. Launch
        try:
            client.tables.create(
                f"{prefix}_Launch",
                {
                    f"{prefix}_TargetDate": "datetime",
                    f"{prefix}_Description": "memo",
                    f"{prefix}_LaunchStatus": LaunchStatus,
                },
                solution=solution_name,
                primary_column=f"{prefix}_Name",
            )
            print("  Created: lc_Launch")
        except Exception as e:
            print(f"  lc_Launch: {e}" if not _is_duplicate(e) else "  lc_Launch already exists.")

        # 2. Milestone
        try:
            client.tables.create(
                f"{prefix}_Milestone",
                {
                    f"{prefix}_DueDate": "datetime",
                    f"{prefix}_SortOrder": "integer",
                    f"{prefix}_MilestoneStatus": MilestoneStatus,
                },
                solution=solution_name,
                primary_column=f"{prefix}_Name",
            )
            print("  Created: lc_Milestone")
        except Exception as e:
            print(f"  lc_Milestone: {e}" if not _is_duplicate(e) else "  lc_Milestone already exists.")

        # 3. Task
        try:
            client.tables.create(
                f"{prefix}_Task",
                {
                    f"{prefix}_DueDate": "datetime",
                    f"{prefix}_Description": "memo",
                    f"{prefix}_IsBlocked": "boolean",
                    f"{prefix}_BlockerReason": "string",
                    f"{prefix}_TaskStatus": TaskStatus,
                },
                solution=solution_name,
                primary_column=f"{prefix}_Title",
            )
            print("  Created: lc_Task")
        except Exception as e:
            print(f"  lc_Task: {e}" if not _is_duplicate(e) else "  lc_Task already exists.")

        # 4. TeamMember
        try:
            client.tables.create(
                f"{prefix}_TeamMember",
                {
                    f"{prefix}_Email": "string",
                    f"{prefix}_Role": "string",
                },
                solution=solution_name,
                primary_column=f"{prefix}_Name",
            )
            print("  Created: lc_TeamMember")
        except Exception as e:
            print(f"  lc_TeamMember: {e}" if not _is_duplicate(e) else "  lc_TeamMember already exists.")

        # 5. StatusUpdate
        try:
            client.tables.create(
                f"{prefix}_StatusUpdate",
                {
                    f"{prefix}_Body": "memo",
                    f"{prefix}_UpdatedOn": "datetime",
                },
                solution=solution_name,
                primary_column=f"{prefix}_Title",
            )
            print("  Created: lc_StatusUpdate")
        except Exception as e:
            print(f"  lc_StatusUpdate: {e}" if not _is_duplicate(e) else "  lc_StatusUpdate already exists.")

        # --- Relationships (Lookups) ---
        print("\nCreating relationships...")
        lookups = [
            (f"{prefix}_Milestone", f"{prefix}_LaunchId", f"{prefix}_Launch", "Launch"),
            (f"{prefix}_Task", f"{prefix}_MilestoneId", f"{prefix}_Milestone", "Milestone"),
            (f"{prefix}_Task", f"{prefix}_AssignedToId", f"{prefix}_TeamMember", "Assigned To"),
            (f"{prefix}_StatusUpdate", f"{prefix}_LaunchId", f"{prefix}_Launch", "Launch"),
            (f"{prefix}_TeamMember", f"{prefix}_LaunchId", f"{prefix}_Launch", "Launch"),
        ]

        for ref_table, lookup_name, target_table, display in lookups:
            try:
                client.tables.create_lookup_field(
                    ref_table,       # referencing_table
                    lookup_name,     # lookup_field_name
                    target_table,    # referenced_table
                    display_name=display,
                    solution=solution_name,
                )
                print(f"  {ref_table} -> {target_table} ({display})")
            except Exception as e:
                if _is_duplicate(e):
                    print(f"  {ref_table} -> {target_table} already exists, skipping.")
                else:
                    print(f"  Error: {ref_table} -> {target_table}: {e}")

        print("\n=== Episode 1 data model complete! ===")
        print("Tables: Launch, Milestone, Task, TeamMember, StatusUpdate")
        print("Columns: status choices, dates, descriptions, blocker flags")
        print("Relationships: Launch->Milestones->Tasks->TeamMembers, StatusUpdates->Launch")


if __name__ == "__main__":
    main()
