"""Session-generated seed: 'Q3 Widget Launch' demo into the lc_ unified layer.

OSS-safe: fictional names, @example.test emails (RFC 2606 reserved domain).
Idempotent: clears the unified tables (in reverse-dependency order) before
inserting. Resolves entity-set names from metadata at runtime (Dataverse's
pluralization is not English plurals: lc_launch -> lc_launchs).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

PREFIX = "lc"

LAUNCH_STATUS = {"OnTrack": 10600101, "AtRisk": 10600102, "Delayed": 10600103,
                 "OnHold": 10600104, "Complete": 10600105}
MILESTONE_STATUS = {"Planned": 10600201, "InProgress": 10600202, "AtRisk": 10600203,
                    "Done": 10600204, "Blocked": 10600205}
TASK_STATUS = {"NotStarted": 10600301, "InProgress": 10600302,
               "Blocked": 10600303, "Done": 10600304}
PRIORITY = {"Critical": 10600401, "High": 10600402, "Medium": 10600403, "Low": 10600404}
CATEGORY = {"Engineering": 10600501, "Marketing": 10600502, "Legal": 10600503,
            "Operations": 10600504, "Planning": 10600505, "Documentation": 10600506,
            "Localization": 10600507, "Tooling": 10600508}
HEALTH = {"Green": 10600601, "Yellow": 10600602, "Red": 10600603}

TEAM = [
    {"name": "Avery Chen",       "email": "avery.chen@example.test",       "role": "Launch Lead"},
    {"name": "Devon Okafor",     "email": "devon.okafor@example.test",     "role": "Engineering Manager"},
    {"name": "Priya Ramaswamy",  "email": "priya.ramaswamy@example.test",  "role": "Product Marketing"},
    {"name": "Jules Martinez",   "email": "jules.martinez@example.test",   "role": "Program Manager"},
]

LAUNCH = {
    "name": "Q3 Widget Launch",
    "code": "WIDGET-Q3",
    "release_window": "2026-Q3",
    "target_date": "2026-09-15",
    "description": ("Public launch of the next-generation Widget product line, "
                    "spanning Engineering, Marketing, Legal, Ops, Docs, and Localization."),
    "status": "OnTrack",
    "priority": "High",
    "owner": "Avery Chen",
}

# (name, quarter, due, description, status, owner)
MILESTONES = [
    ("Eng: Widget API GA",        "2026-Q3", "2026-08-10",
     "Widget Public API reaches GA with v1 contract frozen.",                 "InProgress", "Devon Okafor"),
    ("Marketing: Launch Site",    "2026-Q3", "2026-09-01",
     "Marketing site live with hero, pricing, and demo video.",               "Planned",    "Priya Ramaswamy"),
    ("Legal: Terms & DPA",        "2026-Q3", "2026-08-20",
     "Updated ToS and DPA published; legal sign-off recorded.",               "AtRisk",     "Jules Martinez"),
    ("Ops: Capacity Plan",        "2026-Q3", "2026-08-25",
     "Region-by-region capacity plan with autoscale headroom.",               "InProgress", "Devon Okafor"),
    ("Docs: Public Reference",    "2026-Q3", "2026-09-05",
     "Reference docs and quickstart published on docs portal.",               "Planned",    "Avery Chen"),
    ("Loc: Top-5 Languages",      "2026-Q3", "2026-09-10",
     "Marketing + docs translated for top-5 markets.",                        "Blocked",    "Jules Martinez"),
]

# (title, due, notes, status, priority, category, milestone_idx, assignee)
TASKS = [
    ("Finalize v1 API spec",         "2026-07-25", "Lock request/response schemas; circulate for review.",
        "Done",       "Critical", "Engineering",   0, "Devon Okafor"),
    ("Implement rate limiter",       "2026-08-05", "Token-bucket per tenant; emit metrics.",
        "InProgress", "High",     "Engineering",   0, "Devon Okafor"),
    ("Load test API at 5x peak",     "2026-08-08", "Target P99 < 250ms; document headroom.",
        "NotStarted", "High",     "Engineering",   0, "Avery Chen"),
    ("Hero copy + visuals",          "2026-08-22", "Final hero treatment; A/B variants approved.",
        "InProgress", "Medium",   "Marketing",     1, "Priya Ramaswamy"),
    ("Launch video (90s)",           "2026-08-28", "Voiceover + captions; QA on mobile autoplay.",
        "InProgress", "Medium",   "Marketing",     1, "Priya Ramaswamy"),
    ("Update Terms of Service",      "2026-08-15", "Incorporate new data-residency clauses.",
        "Blocked",    "Critical", "Legal",         2, "Jules Martinez"),
    ("DPA addendum review",          "2026-08-18", "External counsel to confirm regional addenda.",
        "InProgress", "High",     "Legal",         2, "Jules Martinez"),
    ("Region capacity model",        "2026-08-15", "Spreadsheet with growth assumptions per region.",
        "Done",       "High",     "Operations",    3, "Devon Okafor"),
    ("Autoscale runbook",            "2026-08-22", "On-call playbook for scale events; dry-run completed.",
        "InProgress", "Medium",   "Operations",    3, "Avery Chen"),
    ("Quickstart tutorial",          "2026-08-30", "End-to-end tutorial with copy-paste code samples.",
        "NotStarted", "Medium",   "Documentation", 4, "Avery Chen"),
    ("API reference generation",     "2026-09-02", "Wire OpenAPI -> docs portal pipeline.",
        "InProgress", "Medium",   "Documentation", 4, "Devon Okafor"),
    ("Translation vendor contract",  "2026-08-12", "Vendor selection blocked pending procurement approval.",
        "Blocked",    "High",     "Localization",  5, "Jules Martinez"),
]

# (title, summary, days_ago, health, scope_kind, scope_idx, author)
UPDATES = [
    ("Weekly launch sync",
     "Overall on track. Legal and Loc are the two risk areas; mitigation in motion.",
     1, "Yellow", "launch",    None, "Avery Chen"),
    ("Eng update: API GA",
     "Spec frozen, rate limiter ~70% complete, load test scheduled next week.",
     2, "Green",  "milestone", 0,    "Devon Okafor"),
    ("Legal blocker: Terms update",
     "External counsel turnaround slipped a week; escalated to launch lead.",
     3, "Red",    "milestone", 2,    "Jules Martinez"),
    ("Loc vendor contract pending",
     "Procurement approval pending CFO review; ETA Friday.",
     1, "Red",    "task",      11,   "Jules Martinez"),
]


def _delete_all(client, table: str) -> None:
    pk = f"{table}id"
    n = 0
    for page in client.records.get(table, select=[pk]):
        for row in page:
            client.records.delete(table, row[pk])
            n += 1
    if n:
        print(f"  - cleared {n} {table}")


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    with DataverseClient(env_url, get_credential()) as client:
        eset = {}
        for t in (f"{PREFIX}_launch", f"{PREFIX}_milestone", f"{PREFIX}_task",
                  f"{PREFIX}_teammember", f"{PREFIX}_statusupdate"):
            eset[t] = client.tables.get(t).entity_set_name

        print("== Clearing prior demo rows ==")
        for tbl in (f"{PREFIX}_statusupdate", f"{PREFIX}_task",
                    f"{PREFIX}_milestone", f"{PREFIX}_launch", f"{PREFIX}_teammember"):
            _delete_all(client, tbl)

        print("\n== Team members ==")
        team_ids = {}
        for m in TEAM:
            tid = client.records.create(f"{PREFIX}_teammember", {
                f"{PREFIX}_name":  m["name"],
                f"{PREFIX}_email": m["email"],
                f"{PREFIX}_role":  m["role"],
            })
            team_ids[m["name"]] = tid
            print(f"  + {m['name']} ({m['role']})")

        print("\n== Launch ==")
        launch_id = client.records.create(f"{PREFIX}_launch", {
            f"{PREFIX}_name":          LAUNCH["name"],
            f"{PREFIX}_code":          LAUNCH["code"],
            f"{PREFIX}_releasewindow": LAUNCH["release_window"],
            f"{PREFIX}_targetdate":    LAUNCH["target_date"],
            f"{PREFIX}_description":   LAUNCH["description"],
            f"{PREFIX}_launchstatus":  LAUNCH_STATUS[LAUNCH["status"]],
            f"{PREFIX}_priority":      PRIORITY[LAUNCH["priority"]],
            f"{PREFIX}_ownerid@odata.bind":
                f"/{eset[PREFIX + '_teammember']}({team_ids[LAUNCH['owner']]})",
        })
        print(f"  + {LAUNCH['name']}")

        print("\n== Milestones ==")
        milestone_ids = []
        for name, qtr, due, desc, status, owner in MILESTONES:
            mid = client.records.create(f"{PREFIX}_milestone", {
                f"{PREFIX}_name":            name,
                f"{PREFIX}_quarter":         qtr,
                f"{PREFIX}_duedate":         due,
                f"{PREFIX}_description":     desc,
                f"{PREFIX}_milestonestatus": MILESTONE_STATUS[status],
                f"{PREFIX}_launchid@odata.bind":
                    f"/{eset[PREFIX + '_launch']}({launch_id})",
                f"{PREFIX}_ownerid@odata.bind":
                    f"/{eset[PREFIX + '_teammember']}({team_ids[owner]})",
            })
            milestone_ids.append(mid)
            print(f"  + {name} [{status}]")

        print("\n== Tasks ==")
        task_ids = []
        for title, due, notes, status, prio, cat, mi, assignee in TASKS:
            tid = client.records.create(f"{PREFIX}_task", {
                f"{PREFIX}_title":      title,
                f"{PREFIX}_duedate":    due,
                f"{PREFIX}_notes":      notes,
                f"{PREFIX}_taskstatus": TASK_STATUS[status],
                f"{PREFIX}_priority":   PRIORITY[prio],
                f"{PREFIX}_category":   CATEGORY[cat],
                f"{PREFIX}_milestoneid@odata.bind":
                    f"/{eset[PREFIX + '_milestone']}({milestone_ids[mi]})",
                f"{PREFIX}_launchid@odata.bind":
                    f"/{eset[PREFIX + '_launch']}({launch_id})",
                f"{PREFIX}_assignedtoid@odata.bind":
                    f"/{eset[PREFIX + '_teammember']}({team_ids[assignee]})",
            })
            task_ids.append(tid)
            marker = " (BLOCKED)" if status == "Blocked" else ""
            print(f"  + {title} [{status}, {prio}]{marker}")

        print("\n== Status updates ==")
        now = datetime.now(timezone.utc)
        for title, summary, days_ago, health, scope, idx, author in UPDATES:
            payload = {
                f"{PREFIX}_title":    title,
                f"{PREFIX}_summary":  summary,
                f"{PREFIX}_postedat": (now - timedelta(days=days_ago)).isoformat(),
                f"{PREFIX}_health":   HEALTH[health],
                f"{PREFIX}_authorid@odata.bind":
                    f"/{eset[PREFIX + '_teammember']}({team_ids[author]})",
            }
            if scope == "launch":
                payload[f"{PREFIX}_launchid@odata.bind"] = \
                    f"/{eset[PREFIX + '_launch']}({launch_id})"
            elif scope == "milestone":
                payload[f"{PREFIX}_milestoneid@odata.bind"] = \
                    f"/{eset[PREFIX + '_milestone']}({milestone_ids[idx]})"
            elif scope == "task":
                payload[f"{PREFIX}_taskid@odata.bind"] = \
                    f"/{eset[PREFIX + '_task']}({task_ids[idx]})"
            client.records.create(f"{PREFIX}_statusupdate", payload)
            print(f"  + {title} [{health}]")

        blocked = sum(1 for t in TASKS if t[3] == "Blocked")
        print(f"\n=== Done: 1 launch, {len(MILESTONES)} milestones, "
              f"{len(TASKS)} tasks ({blocked} blocked), "
              f"{len(UPDATES)} status updates, {len(TEAM)} team members ===")


if __name__ == "__main__":
    main()
