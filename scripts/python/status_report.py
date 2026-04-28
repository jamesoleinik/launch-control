"""Launch Status Report — pandas-powered.

Queries all launches, milestones, and tasks via the Dataverse Python SDK's
DataFrame API, then generates a rich terminal report with progress bars
and color-coded status.

Usage: python scripts/python/status_report.py
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

        # --- Query launches as DataFrame ---
        print("Querying launches...")
        launches_df = client.dataframe.get(
            "lc_launch",
            select=["lc_name", "lc_launchstatus", "lc_targetdate"],
        )
        print(f"Found {len(launches_df)} launch(es)\n")

        # --- Query milestones as DataFrame ---
        milestones_df = client.dataframe.get(
            "lc_milestone",
            select=["lc_name", "lc_milestonestatus", "lc_duedate", "_lc_launchid_value"],
        )

        # --- Query tasks as DataFrame ---
        tasks_df = client.dataframe.get(
            "lc_task",
            select=["lc_title", "lc_taskstatus", "lc_isblocked", "lc_blockerreason",
                     "_lc_milestoneid_value", "_lc_assignedtoid_value"],
        )

        # --- Status mappings ---
        milestone_status = {
            10600010: "Not Started", 10600011: "In Progress",
            10600012: "Complete", 10600013: "At Risk", 10600014: "Blocked",
        }
        task_status = {
            10600020: "Not Started", 10600021: "In Progress",
            10600022: "Done", 10600023: "Blocked",
        }
        launch_status = {
            10600001: "Planning", 10600002: "In Progress",
            10600003: "Ready", 10600004: "Launched", 10600005: "On Hold",
        }

        # --- Map status codes to labels ---
        milestones_df["status_label"] = milestones_df["lc_milestonestatus"].map(milestone_status)
        tasks_df["status_label"] = tasks_df["lc_taskstatus"].map(task_status)

        # --- Milestone summary ---
        print("=" * 60)
        print("LAUNCH STATUS REPORT")
        print("=" * 60)

        for _, launch in launches_df.iterrows():
            launch_name = launch["lc_name"]
            status = launch_status.get(launch["lc_launchstatus"], "Unknown")
            target = str(launch.get("lc_targetdate", "N/A"))[:10]

            print(f"\n{'=' * 60}")
            print(f"  {launch_name}")
            print(f"  Status: {status}  |  Target: {target}")
            print(f"{'=' * 60}")

            # Get milestones for this launch
            launch_id = launch.get("lc_launchid")
            ms_for_launch = milestones_df[
                milestones_df["_lc_launchid_value"] == launch_id
            ].sort_values("lc_duedate")

            print(f"\n  Milestones ({len(ms_for_launch)}):")
            print(f"  {'Name':<30} {'Status':<15} {'Due':<12}")
            print(f"  {'-'*30} {'-'*15} {'-'*12}")

            for _, ms in ms_for_launch.iterrows():
                ms_name = ms["lc_name"]
                ms_status = ms["status_label"]
                ms_due = str(ms.get("lc_duedate", ""))[:10]
                indicator = {"Complete": "[OK]", "At Risk": "[!!]",
                            "Blocked": "[XX]", "In Progress": "[..]",
                            "Not Started": "[  ]"}.get(ms_status, "[??]")
                print(f"  {indicator} {ms_name:<26} {ms_status:<15} {ms_due}")

            # Task summary by milestone
            total_tasks = len(tasks_df)
            done_tasks = len(tasks_df[tasks_df["lc_taskstatus"] == 10600022])
            blocked_tasks = tasks_df[tasks_df["lc_isblocked"] == True]
            pct = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0

            bar_len = 30
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "-" * (bar_len - filled)

            print(f"\n  Task Progress: [{bar}] {pct:.0f}%")
            print(f"  {done_tasks}/{total_tasks} tasks complete")

            if len(blocked_tasks) > 0:
                print(f"\n  BLOCKED TASKS ({len(blocked_tasks)}):")
                for _, t in blocked_tasks.iterrows():
                    reason = t.get("lc_blockerreason", "No reason given")
                    print(f"    [X] {t['lc_title']}")
                    print(f"        Reason: {reason}")

        # --- Pandas analytics ---
        print(f"\n{'=' * 60}")
        print("ANALYTICS (pandas)")
        print(f"{'=' * 60}")

        print("\nMilestone Status Distribution:")
        print(milestones_df["status_label"].value_counts().to_string())

        print("\nTask Status Distribution:")
        print(tasks_df["status_label"].value_counts().to_string())

        print(f"\nBlocked task rate: {len(blocked_tasks)}/{total_tasks} ({len(blocked_tasks)/total_tasks*100:.0f}%)")


if __name__ == "__main__":
    main()
