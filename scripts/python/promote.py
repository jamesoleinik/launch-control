"""Promote LaunchControl staging trackers into the unified data model.

Topology:
    lc_stg_tracker_a → lc_task       (lookup: lc_sourcestagingaid)
    lc_stg_tracker_b → lc_task       (lookup: lc_sourcestagingbid)
    lc_stg_tracker_c → lc_milestone  (lookup: lc_sourcestagingcid)
    lc_stg_tracker_d → lc_task       (lookup: lc_sourcestagingdid)
    lc_stg_tracker_e → lc_milestone  (lookup: lc_sourcestagingeid)

Idempotency contract:
    1. Dedupe staging rows by lc_sourceid (keep latest modifiedon).
    2. Look up the unified twin via the back-reference lookup
       (_lc_sourcestaging<x>id_value) → update in place if present, else create.
    3. Always bind lc_sourcestaging<x>id@odata.bind on the write so the
       lookup is set on first create AND survives updates.

Final step: no-op update on the singleton lc_launch row so Dataverse
re-evaluates the lc_risksummary prompt column.

CLI:
    python scripts/python/promote.py
    python scripts/python/promote.py --dry-run
    python scripts/python/promote.py --tracker TrackerA
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402


# ---------------------------------------------------------------------------
# Option-set values (re-discover via EntityDefinitions(...) /Attributes(...)
# /Microsoft.Dynamics.CRM.PicklistAttributeMetadata?$expand=OptionSet if you
# ever rebuild this env from scratch).
# ---------------------------------------------------------------------------

TASK_STATUS = {
    "NotStarted": 10600301, "InProgress": 10600302,
    "Blocked":    10600303, "Done":       10600304,
}
MILESTONE_STATUS = {
    "Planned":    10600201, "NotStarted": 10600201,
    "InProgress": 10600202, "OnTrack":    10600202,
    "AtRisk":     10600203,
    "Done":       10600204, "Complete":   10600204,
    "Blocked":    10600205, "Delayed":    10600205,
}
TASK_PRIORITY = {
    "Critical": 10600401, "High":   10600402,
    "Medium":   10600403, "Low":    10600404,
}
TASK_CATEGORY = {
    "Engineering":   10600501, "Marketing":     10600502,
    "Legal":         10600503, "Operations":    10600504,
    "Planning":      10600505, "Documentation": 10600506,
    "Localization":  10600507, "Tooling":       10600508,
}
TASK_SOURCETRACKER = {
    "TrackerA": 10600701, "TrackerB": 10600702, "TrackerD": 10600703,
}

# Entity sets (this env follows the lowercase + trailing 's' convention).
ES = {
    "lc_launch":          "lc_launchs",
    "lc_milestone":       "lc_milestones",
    "lc_task":            "lc_tasks",
    "lc_teammember":      "lc_teammembers",
    "lc_stg_tracker_a":   "lc_stg_tracker_as",
    "lc_stg_tracker_b":   "lc_stg_tracker_bs",
    "lc_stg_tracker_c":   "lc_stg_tracker_cs",
    "lc_stg_tracker_d":   "lc_stg_tracker_ds",
    "lc_stg_tracker_e":   "lc_stg_tracker_es",
}


# ---------------------------------------------------------------------------
# Quarter helpers
# ---------------------------------------------------------------------------

_QUARTER_END_MONTH = {1: 3, 2: 6, 3: 9, 4: 12}
_FISCAL_OFFSET = 6  # MS-style FY starts in July → FYxx Q1 == calendar Jul–Sep of (xx-1)


def _last_day(year: int, month: int) -> str:
    if month == 12:
        return f"{year}-12-31"
    nxt = date(year, month + 1, 1)
    last = nxt.toordinal() - 1
    d = date.fromordinal(last)
    return d.isoformat()


def quarter_to_iso_date(text: str | None) -> str | None:
    """Map '2026Q3' / 'Q3 2026' / 'Q1FY27' / 'FY27Q1' to an ISO end-of-quarter date."""
    if not text:
        return None
    s = str(text).strip().upper().replace(" ", "")

    # Calendar:  2026Q3  or  Q3-2026
    m = re.match(r"^(\d{4})Q([1-4])$", s) or re.match(r"^Q([1-4])-?(\d{4})$", s)
    if m:
        if m.re.pattern.startswith("^(\\d{4})"):
            year, q = int(m.group(1)), int(m.group(2))
        else:
            q, year = int(m.group(1)), int(m.group(2))
        return _last_day(year, _QUARTER_END_MONTH[q])

    # Fiscal:  Q1FY27  or  FY27Q1
    m = re.match(r"^Q([1-4])FY(\d{2,4})$", s) or re.match(r"^FY(\d{2,4})Q([1-4])$", s)
    if m:
        if m.re.pattern.startswith("^Q"):
            q, fy = int(m.group(1)), int(m.group(2))
        else:
            fy, q = int(m.group(1)), int(m.group(2))
        if fy < 100:
            fy += 2000
        cal_year = fy - 1  # FY27 Q1 = Jul-Sep 2026
        cal_month = ((_FISCAL_OFFSET + (q - 1) * 3) % 12) + 1
        cal_year_adj = cal_year + ((_FISCAL_OFFSET + (q - 1) * 3) // 12)
        end_month = cal_month + 2
        if end_month > 12:
            end_month -= 12
            cal_year_adj += 1
        return _last_day(cal_year_adj, end_month)

    return None


def release_to_quarter(release: str | None) -> str | None:
    """Best-effort release-string → quarter token (e.g. 'v2.0 Q3 2026' → '2026Q3')."""
    if not release:
        return None
    s = str(release).upper()
    m = re.search(r"Q([1-4]).{0,5}(\d{4})", s) or re.search(r"(\d{4}).{0,5}Q([1-4])", s)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    if len(a) == 4:
        return f"{a}Q{b}"
    return f"{b}Q{a}"


# ---------------------------------------------------------------------------
# Context cache (singleton launch + lookup resolvers)
# ---------------------------------------------------------------------------

def build_context(client) -> dict[str, Any]:
    launches = client.dataframe.get("lc_launch", select=["lc_launchid", "lc_name"])
    if len(launches) == 0:
        raise SystemExit("No lc_launch row found — seed the singleton launch first.")
    launch = launches.iloc[0]
    members = client.dataframe.get(
        "lc_teammember", select=["lc_teammemberid", "lc_email", "lc_name"],
    )
    member_by_email: dict[str, str] = {}
    if "lc_email" in members.columns:
        for _, r in members.iterrows():
            email = (r.get("lc_email") or "").strip().lower()
            if email:
                member_by_email[email] = r["lc_teammemberid"]

    milestones = client.dataframe.get(
        "lc_milestone", select=["lc_milestoneid", "lc_name"],
    )
    milestone_by_name: dict[str, str] = {}
    if "lc_name" in milestones.columns:
        for _, r in milestones.iterrows():
            n = (r.get("lc_name") or "").strip().lower()
            if n:
                milestone_by_name[n] = r["lc_milestoneid"]

    return {
        "launch_id": launch["lc_launchid"],
        "launch_name": launch["lc_name"],
        "member_by_email": member_by_email,
        "milestone_by_name": milestone_by_name,
    }


def refresh_milestones(client, ctx: dict[str, Any]) -> None:
    df = client.dataframe.get("lc_milestone", select=["lc_milestoneid", "lc_name"])
    idx: dict[str, str] = {}
    for _, r in df.iterrows():
        n = (r.get("lc_name") or "").strip().lower()
        if n:
            idx[n] = r["lc_milestoneid"]
    ctx["milestone_by_name"] = idx


# ---------------------------------------------------------------------------
# Build index of unified rows keyed by back-reference lookup
# ---------------------------------------------------------------------------

def load_index(client, target: str, pk: str, lookup: str) -> dict[str, str]:
    # Lookup columns must be selected by their `_value` projection name
    # — selecting the bare logical name silently drops the column.
    value_col = f"_{lookup}_value"
    df = client.dataframe.get(target, select=[pk, value_col])
    out: dict[str, str] = {}
    if value_col not in df.columns:
        return out
    for _, r in df.iterrows():
        staging_id = r.get(value_col)
        if pd.isna(staging_id) or not staging_id:
            continue
        out[str(staging_id)] = r[pk]
    return out


# ---------------------------------------------------------------------------
# Per-tracker recipes
# ---------------------------------------------------------------------------

def _common_task_lookups(row: pd.Series, ctx: dict[str, Any], body: dict[str, Any]) -> None:
    body[f"lc_launchid@odata.bind"] = f"/{ES['lc_launch']}({ctx['launch_id']})"
    email = (row.get("lc_owneremail") or "").strip().lower()
    if email and email in ctx["member_by_email"]:
        body["lc_assignedtoid@odata.bind"] = (
            f"/{ES['lc_teammember']}({ctx['member_by_email'][email]})"
        )
    hint = (row.get("lc_milestonename") or "").strip().lower()
    if hint and hint in ctx["milestone_by_name"]:
        body["lc_milestoneid@odata.bind"] = (
            f"/{ES['lc_milestone']}({ctx['milestone_by_name'][hint]})"
        )


def recipe_a(row: pd.Series, ctx: dict[str, Any]) -> dict[str, Any]:
    status = (row.get("lc_status") or "NotStarted").strip()
    body: dict[str, Any] = {
        "lc_title":  row.get("lc_title"),
        "lc_notes":  row.get("lc_notes"),
        "lc_duedate": row.get("lc_duedate"),
        "lc_taskstatus": TASK_STATUS.get(status, TASK_STATUS["NotStarted"]),
        "lc_sourcetracker": TASK_SOURCETRACKER["TrackerA"],
    }
    prio = (row.get("lc_priority") or "").strip()
    if prio in TASK_PRIORITY:
        body["lc_priority"] = TASK_PRIORITY[prio]
    if status == "Blocked":
        body["lc_isblocked"] = True
        body["lc_blockerreason"] = (row.get("lc_notes") or "").strip() or "(no detail in source)"
    _common_task_lookups(row, ctx, body)
    return body


def recipe_b(row: pd.Series, ctx: dict[str, Any]) -> dict[str, Any]:
    status = (row.get("lc_status") or "NotStarted").strip()
    category = (row.get("lc_category") or "").strip()
    body: dict[str, Any] = {
        "lc_title":  row.get("lc_name"),
        "lc_duedate": row.get("lc_duedate"),
        "lc_taskstatus": TASK_STATUS.get(status, TASK_STATUS["NotStarted"]),
        "lc_sourcetracker": TASK_SOURCETRACKER["TrackerB"],
    }
    prio = (row.get("lc_priority") or "").strip()
    if prio in TASK_PRIORITY:
        body["lc_priority"] = TASK_PRIORITY[prio]
    if category in TASK_CATEGORY:
        body["lc_category"] = TASK_CATEGORY[category]
    if status == "Blocked":
        body["lc_isblocked"] = True
        body["lc_blockerreason"] = f"[{category}] (no detail in source)" if category else "(no detail in source)"
    _common_task_lookups(row, ctx, body)
    return body


def recipe_c(row: pd.Series, ctx: dict[str, Any]) -> dict[str, Any]:
    status = (row.get("lc_status") or "Planned").strip()
    quarter = (row.get("lc_quarter") or "").strip()
    body: dict[str, Any] = {
        "lc_name": row.get("lc_initiative"),
        "lc_milestonestatus": MILESTONE_STATUS.get(status, MILESTONE_STATUS["Planned"]),
        "lc_quarter": quarter or None,
        "lc_duedate": quarter_to_iso_date(quarter),
        "lc_launchid@odata.bind": f"/{ES['lc_launch']}({ctx['launch_id']})",
    }
    email = (row.get("lc_owneremail") or "").strip().lower()
    if email and email in ctx["member_by_email"]:
        body["lc_ownerid@odata.bind"] = (
            f"/{ES['lc_teammember']}({ctx['member_by_email'][email]})"
        )
    return body


def recipe_d(row: pd.Series, ctx: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "lc_title":  row.get("lc_tool"),
        "lc_notes":  row.get("lc_notes"),
        "lc_taskstatus": TASK_STATUS["NotStarted"],
        "lc_category": TASK_CATEGORY["Tooling"],
        "lc_sourcetracker": TASK_SOURCETRACKER["TrackerD"],
    }
    prio = (row.get("lc_priority") or "").strip()
    if prio in TASK_PRIORITY:
        body["lc_priority"] = TASK_PRIORITY[prio]
    _common_task_lookups(row, ctx, body)
    return body


def recipe_e(row: pd.Series, ctx: dict[str, Any]) -> dict[str, Any]:
    status = (row.get("lc_status") or "OnTrack").strip()
    project = (row.get("lc_project") or "").strip()
    release = (row.get("lc_release") or "").strip()
    name = f"{project} ({release})" if project and release else (project or release)
    qtoken = release_to_quarter(release) or release
    body: dict[str, Any] = {
        "lc_name": name,
        "lc_milestonestatus": MILESTONE_STATUS.get(status, MILESTONE_STATUS["Planned"]),
        "lc_duedate": quarter_to_iso_date(qtoken),
        "lc_launchid@odata.bind": f"/{ES['lc_launch']}({ctx['launch_id']})",
    }
    email = (row.get("lc_owneremail") or "").strip().lower()
    if email and email in ctx["member_by_email"]:
        body["lc_ownerid@odata.bind"] = (
            f"/{ES['lc_teammember']}({ctx['member_by_email'][email]})"
        )
    return body


# ---------------------------------------------------------------------------
# Tracker plan
# ---------------------------------------------------------------------------

class TrackerPlan:
    def __init__(
        self,
        name: str,
        source: str,
        source_pk: str,
        target: str,
        target_pk: str,
        lookup_attr: str,
        recipe: Callable[[pd.Series, dict[str, Any]], dict[str, Any]],
        select: list[str],
    ) -> None:
        self.name = name
        self.source = source
        self.source_pk = source_pk
        self.target = target
        self.target_pk = target_pk
        self.lookup_attr = lookup_attr
        self.recipe = recipe
        self.select = select


PLANS: list[TrackerPlan] = [
    # Milestones first so the task trackers can resolve milestone hints.
    TrackerPlan(
        name="TrackerC",
        source="lc_stg_tracker_c", source_pk="lc_stg_tracker_cid",
        target="lc_milestone", target_pk="lc_milestoneid",
        lookup_attr="lc_sourcestagingcid",
        recipe=recipe_c,
        select=["lc_stg_tracker_cid", "lc_sourceid", "modifiedon",
                "lc_initiative", "lc_quarter", "lc_status", "lc_owneremail"],
    ),
    TrackerPlan(
        name="TrackerE",
        source="lc_stg_tracker_e", source_pk="lc_stg_tracker_eid",
        target="lc_milestone", target_pk="lc_milestoneid",
        lookup_attr="lc_sourcestagingeid",
        recipe=recipe_e,
        select=["lc_stg_tracker_eid", "lc_sourceid", "modifiedon",
                "lc_project", "lc_release", "lc_status", "lc_priority", "lc_owneremail"],
    ),
    TrackerPlan(
        name="TrackerA",
        source="lc_stg_tracker_a", source_pk="lc_stg_tracker_aid",
        target="lc_task", target_pk="lc_taskid",
        lookup_attr="lc_sourcestagingaid",
        recipe=recipe_a,
        select=["lc_stg_tracker_aid", "lc_sourceid", "modifiedon",
                "lc_title", "lc_notes", "lc_duedate", "lc_status",
                "lc_priority", "lc_owneremail", "lc_milestonename"],
    ),
    TrackerPlan(
        name="TrackerB",
        source="lc_stg_tracker_b", source_pk="lc_stg_tracker_bid",
        target="lc_task", target_pk="lc_taskid",
        lookup_attr="lc_sourcestagingbid",
        recipe=recipe_b,
        select=["lc_stg_tracker_bid", "lc_sourceid", "modifiedon",
                "lc_name", "lc_category", "lc_duedate", "lc_status",
                "lc_priority", "lc_owneremail", "lc_milestonename"],
    ),
    TrackerPlan(
        name="TrackerD",
        source="lc_stg_tracker_d", source_pk="lc_stg_tracker_did",
        target="lc_task", target_pk="lc_taskid",
        lookup_attr="lc_sourcestagingdid",
        recipe=recipe_d,
        select=["lc_stg_tracker_did", "lc_sourceid", "modifiedon",
                "lc_tool", "lc_notes", "lc_priority", "lc_owneremail",
                "lc_milestonename"],
    ),
]


# ---------------------------------------------------------------------------
# Per-tracker promotion
# ---------------------------------------------------------------------------

def _scrub_nans(body: dict[str, Any]) -> dict[str, Any]:
    """Drop NaN / None / empty-string values so we don't clobber server columns."""
    clean: dict[str, Any] = {}
    for k, v in body.items():
        if v is None:
            continue
        if isinstance(v, float) and pd.isna(v):
            continue
        if isinstance(v, str) and not v.strip():
            continue
        clean[k] = v
    return clean


def promote_tracker(
    client,
    plan: TrackerPlan,
    ctx: dict[str, Any],
    dry_run: bool,
) -> dict[str, int]:
    print(f"-> {plan.source}  →  {plan.target}")

    raw = client.dataframe.get(plan.source, select=plan.select)
    n_read = len(raw)

    # Dedupe by lc_sourceid (keep latest modifiedon).
    if "lc_sourceid" in raw.columns and n_read > 0:
        deduped = (
            raw.sort_values("modifiedon", ascending=True, na_position="first")
               .drop_duplicates(subset=["lc_sourceid"], keep="last")
        )
    else:
        deduped = raw
    n_dedup = len(deduped)

    index = load_index(client, plan.target, plan.target_pk, plan.lookup_attr)

    created = updated = skipped = 0
    source_es = ES[plan.source]
    bind_attr = f"{plan.lookup_attr}@odata.bind"

    for _, row in deduped.iterrows():
        staging_guid = row.get(plan.source_pk)
        if pd.isna(staging_guid) or not staging_guid:
            skipped += 1
            continue
        body = plan.recipe(row, ctx)
        body = _scrub_nans(body)
        # Always bind the back-reference lookup — this IS the upsert key.
        body[bind_attr] = f"/{source_es}({staging_guid})"

        existing = index.get(str(staging_guid))
        if dry_run:
            if existing:
                updated += 1
            else:
                created += 1
            continue

        try:
            if existing:
                client.records.update(plan.target, existing, body)
                updated += 1
            else:
                client.records.create(plan.target, body)
                created += 1
        except Exception as exc:  # noqa: BLE001
            print(f"   ! failed row {staging_guid}: {exc.__class__.__name__}: {exc}")
            skipped += 1

    print(f"    read={n_read}  deduped={n_dedup}  created={created}  "
          f"updated={updated}  skipped={skipped}")
    return {
        "read": n_read, "deduped": n_dedup,
        "created": created, "updated": updated, "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Launch touch — re-evaluates the lc_risksummary prompt column
# ---------------------------------------------------------------------------

def _touch_launch(client, ctx: dict[str, Any]) -> None:
    launch_id = ctx.get("launch_id")
    name = ctx.get("launch_name")
    if not launch_id or not name:
        return
    client.records.update("lc_launch", launch_id, {"lc_name": name})
    print(f"  Touched lc_launch ({name}) to trigger prompt-column refresh.")


# ---------------------------------------------------------------------------
# Row-count snapshot (the before/after the on-camera demo bracket)
# ---------------------------------------------------------------------------

def snapshot(client) -> tuple[int, int]:
    m = len(client.dataframe.get("lc_milestone", select=["lc_milestoneid"]))
    t = len(client.dataframe.get("lc_task", select=["lc_taskid"]))
    return m, t


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would change without writing.")
    ap.add_argument("--tracker", choices=[p.name for p in PLANS],
                    help="Promote a single tracker instead of all five.")
    args = ap.parse_args()

    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")

    plans = [p for p in PLANS if (args.tracker is None or p.name == args.tracker)]

    with DataverseClient(url, get_credential()) as client:
        ctx = build_context(client)

        before_m, before_t = snapshot(client)
        print(f"Before:  lc_milestone={before_m}   lc_task={before_t}")
        print()

        totals = {"read": 0, "deduped": 0, "created": 0, "updated": 0, "skipped": 0}
        for plan in plans:
            stats = promote_tracker(client, plan, ctx, dry_run=args.dry_run)
            for k, v in stats.items():
                totals[k] += v
            # After milestones promote, refresh the milestone-name index so
            # task trackers can resolve their free-text hints.
            if plan.target == "lc_milestone" and not args.dry_run:
                refresh_milestones(client, ctx)
            print()

        if not args.dry_run:
            _touch_launch(client, ctx)

        print()
        print("=== Promotion complete ===")
        print(f"  rows read     {totals['read']}")
        print(f"  rows deduped  {totals['deduped']}")
        print(f"  rows created  {totals['created']}")
        print(f"  rows updated  {totals['updated']}")
        print(f"  rows skipped  {totals['skipped']}")

        if args.dry_run:
            print("\n(--dry-run: no writes performed; row counts not re-read)")
        else:
            after_m, after_t = snapshot(client)
            d_m = after_m - before_m
            d_t = after_t - before_t
            print(f"\nAfter:   lc_milestone={after_m}  lc_task={after_t}   "
                  f"(delta: +{d_m} / +{d_t})")


if __name__ == "__main__":
    main()
