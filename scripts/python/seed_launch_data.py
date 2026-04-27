"""Seed the Q3 Widget Launch with realistic sample data.

Creates:
- 1 Launch: Q3 Widget Launch
- 5 Team Members
- 4 Milestones (Engineering, QA, Marketing, Legal)
- 12 Tasks across milestones (some blocked)
- 3 Status Updates
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    prefix = "lc"

    with DataverseClient(env_url, credential) as client:

        # --- Launch ---
        print("Creating Q3 Widget Launch...")
        launch_id = client.records.create("lc_launch", {
            f"{prefix}_name": "Q3 Widget Launch",
            f"{prefix}_targetdate": "2026-09-15",
            f"{prefix}_description": "Cross-team launch of the new Widget feature for Q3. Spans engineering, QA, marketing, and legal.",
            f"{prefix}_launchstatus": 10600002,  # In Progress
        })
        print(f"  Launch: {launch_id}")

        # --- Team Members ---
        print("Creating team members...")
        members = [
            ("Alex Chen", "alex.chen@contoso.com", "Engineering Lead"),
            ("Sarah Kim", "sarah.kim@contoso.com", "QA Lead"),
            ("Marcus Johnson", "marcus.johnson@contoso.com", "Marketing Manager"),
            ("Priya Patel", "priya.patel@contoso.com", "Legal Counsel"),
            ("James Rivera", "james.rivera@contoso.com", "Program Manager"),
        ]
        member_ids = {}
        for name, email, role in members:
            mid = client.records.create("lc_teammember", {
                f"{prefix}_name": name,
                f"{prefix}_email": email,
                f"{prefix}_role": role,
                f"{prefix}_LaunchId@odata.bind": f"/lc_launchs({launch_id})",
            })
            member_ids[name] = mid
            print(f"  {name} ({role})")

        # --- Milestones ---
        print("Creating milestones...")
        milestones = [
            ("Engineering Sign-off", "2026-08-01", 1, 10600012),  # Complete
            ("QA Pass", "2026-08-15", 2, 10600012),               # Complete
            ("Marketing Approval", "2026-08-22", 3, 10600013),    # At Risk
            ("Legal Review", "2026-09-01", 4, 10600010),          # Not Started
        ]
        milestone_ids = {}
        for name, due, sort, status in milestones:
            mid = client.records.create("lc_milestone", {
                f"{prefix}_name": name,
                f"{prefix}_duedate": due,
                f"{prefix}_sortorder": sort,
                f"{prefix}_milestonestatus": status,
                f"{prefix}_LaunchId@odata.bind": f"/lc_launchs({launch_id})",
            })
            milestone_ids[name] = mid
            status_labels = {10600010: "Not Started", 10600011: "In Progress",
                            10600012: "Complete", 10600013: "At Risk", 10600014: "Blocked"}
            print(f"  {name} ({status_labels.get(status, status)})")

        # --- Tasks ---
        print("Creating tasks...")
        tasks = [
            # Engineering tasks (complete)
            ("Implement widget core API", milestone_ids["Engineering Sign-off"],
             member_ids["Alex Chen"], "2026-07-15", 10600022, False, None),
            ("Write unit tests", milestone_ids["Engineering Sign-off"],
             member_ids["Alex Chen"], "2026-07-20", 10600022, False, None),
            ("Performance benchmarks", milestone_ids["Engineering Sign-off"],
             member_ids["Alex Chen"], "2026-07-25", 10600022, False, None),
            # QA tasks (complete)
            ("Integration test suite", milestone_ids["QA Pass"],
             member_ids["Sarah Kim"], "2026-08-05", 10600022, False, None),
            ("Load testing", milestone_ids["QA Pass"],
             member_ids["Sarah Kim"], "2026-08-10", 10600022, False, None),
            ("Security review", milestone_ids["QA Pass"],
             member_ids["Sarah Kim"], "2026-08-14", 10600022, False, None),
            # Marketing tasks (one blocked)
            ("Draft launch blog post", milestone_ids["Marketing Approval"],
             member_ids["Marcus Johnson"], "2026-08-10", 10600022, False, None),
            ("Create demo video", milestone_ids["Marketing Approval"],
             member_ids["Marcus Johnson"], "2026-08-15", 10600021, False, None),
            ("Get VP approval on messaging", milestone_ids["Marketing Approval"],
             member_ids["Marcus Johnson"], "2026-08-18", 10600023, True,
             "VP is on vacation until Aug 25. Cannot get approval until return."),
            # Legal tasks (not started)
            ("Review terms of service update", milestone_ids["Legal Review"],
             member_ids["Priya Patel"], "2026-08-25", 10600020, False, None),
            ("Privacy impact assessment", milestone_ids["Legal Review"],
             member_ids["Priya Patel"], "2026-08-28", 10600020, False, None),
            ("Open source license audit", milestone_ids["Legal Review"],
             member_ids["Priya Patel"], "2026-09-01", 10600020, False, None),
        ]

        for title, ms_id, owner_id, due, status, blocked, reason in tasks:
            data = {
                f"{prefix}_title": title,
                f"{prefix}_duedate": due,
                f"{prefix}_taskstatus": status,
                f"{prefix}_isblocked": blocked,
                f"{prefix}_MilestoneId@odata.bind": f"/lc_milestones({ms_id})",
                f"{prefix}_AssignedToId@odata.bind": f"/lc_teammembers({owner_id})",
            }
            if reason:
                data[f"{prefix}_blockerreason"] = reason
            client.records.create("lc_task", data)
            status_labels = {10600020: "Not Started", 10600021: "In Progress",
                            10600022: "Done", 10600023: "Blocked"}
            flag = " [BLOCKED]" if blocked else ""
            print(f"  {title} ({status_labels.get(status, status)}){flag}")

        # --- Status Updates ---
        print("Creating status updates...")
        updates = [
            ("Week 1: Engineering on track",
             "All engineering tasks completed ahead of schedule. Unit tests passing. Performance benchmarks meet targets.",
             "2026-07-28"),
            ("Week 3: QA complete, marketing risk",
             "QA passed all test suites. Marketing blocker: VP approval pending due to vacation. Legal not yet started.",
             "2026-08-16"),
            ("Week 4: Marketing still blocked",
             "VP returns Aug 25. Marketing milestone at risk. Legal review needs to start this week to stay on schedule.",
             "2026-08-22"),
        ]
        for title, body, date in updates:
            client.records.create("lc_statusupdate", {
                f"{prefix}_title": title,
                f"{prefix}_body": body,
                f"{prefix}_updatedon": date,
                f"{prefix}_LaunchId@odata.bind": f"/lc_launchs({launch_id})",
            })
            print(f"  {title}")

        print(f"\n=== Seed data complete! ===")
        print(f"Launch: Q3 Widget Launch ({launch_id})")
        print(f"Team Members: {len(members)}")
        print(f"Milestones: {len(milestones)} (2 complete, 1 at risk, 1 not started)")
        print(f"Tasks: {len(tasks)} (6 done, 1 in progress, 1 blocked, 4 not started)")
        print(f"Status Updates: {len(updates)}")


if __name__ == "__main__":
    main()
