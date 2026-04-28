"""Escalation Summary — pandas-powered.

Pulls blocked tasks, joins with team members, and generates an
escalation summary grouped by owner.

Usage: python scripts/python/escalation_summary.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient

import pandas as pd


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")

    with DataverseClient(env_url, get_credential()) as client:

        # --- SQL JOIN: tasks with milestones ---
        print("Running SQL JOIN query...")
        results = client.query.sql(
            "SELECT t.lc_title, t.lc_taskstatus, t.lc_isblocked, "
            "t.lc_blockerreason, t.lc_duedate, "
            "m.lc_name as milestone_name, m.lc_milestonestatus "
            "FROM lc_task t "
            "JOIN lc_milestone m ON t.lc_MilestoneId = m.lc_milestoneid"
        )
        df = pd.DataFrame(results)
        print(f"Query returned {len(df)} tasks across milestones\n")

        # --- Get team members ---
        members_df = client.dataframe.get(
            "lc_teammember",
            select=["lc_name", "lc_email", "lc_role", "lc_teammemberid"],
        )

        # --- Get tasks with assigned-to info ---
        tasks_df = client.dataframe.get(
            "lc_task",
            select=["lc_title", "lc_taskstatus", "lc_isblocked",
                     "lc_blockerreason", "lc_duedate", "_lc_assignedtoid_value"],
        )

        # --- Merge tasks with team members ---
        merged = tasks_df.merge(
            members_df,
            left_on="_lc_assignedtoid_value",
            right_on="lc_teammemberid",
            how="left",
        )
        # Rename for clarity
        if "lc_name_x" in merged.columns:
            merged = merged.rename(columns={"lc_name_x": "owner_name"})
        elif "lc_name" in merged.columns:
            merged = merged.rename(columns={"lc_name": "owner_name"})

        # --- Filter to blocked tasks ---
        blocked = merged[merged["lc_isblocked"] == True]

        print("=" * 60)
        print("ESCALATION SUMMARY")
        print("=" * 60)

        if len(blocked) == 0:
            print("\nNo blocked tasks! All clear.")
            return

        # --- Group by owner ---
        for owner, group in blocked.groupby("owner_name"):
            email = group["lc_email"].iloc[0] if "lc_email" in group.columns else "N/A"
            role = group["lc_role"].iloc[0] if "lc_role" in group.columns else "N/A"
            print(f"\n  Owner: {owner} ({role})")
            print(f"  Email: {email}")
            print(f"  Blocked tasks: {len(group)}")
            for _, task in group.iterrows():
                due = str(task.get("lc_duedate", ""))[:10]
                print(f"    [X] {task['lc_title']}")
                print(f"        Due: {due}")
                print(f"        Reason: {task.get('lc_blockerreason', 'No reason')}")

        # --- Summary stats ---
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total blocked tasks: {len(blocked)}")
        print(f"Owners affected: {blocked['owner_name'].nunique()}")
        print(f"\nTasks by status (all):")
        status_map = {10600020: "Not Started", 10600021: "In Progress",
                      10600022: "Done", 10600023: "Blocked"}
        merged["status_label"] = merged["lc_taskstatus"].map(status_map)
        print(merged["status_label"].value_counts().to_string())


if __name__ == "__main__":
    main()
