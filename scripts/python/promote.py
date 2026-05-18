"""Episode 3 — Promote staging tracker rows into the unified Launch model.

Reads:
    datamodel/mappings/unified_mapping.yaml   (which staging table → which unified table)

For every mapping with a `promote_to:` hint:
    1. Pull staging rows from the tracker table (lc_stg_tracker_a..e)
    2. Normalize fields into the unified shape (lc_task / lc_milestone)
    3. Resolve string statuses → unified picklist option-set ints
    4. Upsert keyed on the lookup column `lc_SourceStaging<X>Id`. The lookup
       IS the back-reference — provenance is a real relationship, queryable
       in views and gen pages, not a synthesized string.

Tracker → target topology:
    Tracker A → lc_task         (lookup: lc_sourcestagingaid)
    Tracker B → lc_task         (lookup: lc_sourcestagingbid)
    Tracker C → lc_milestone    (lookup: lc_sourcestagingcid)
    Tracker D → lc_task         (lookup: lc_sourcestagingdid)
    Tracker E → lc_milestone    (lookup: lc_sourcestagingeid)

There is exactly one launch ("Q3 Widget Launch"); every promoted milestone
rolls up to it. The launch row is seeded outside this script.

Idempotent: re-running promotes any new staging rows and updates existing
unified rows in place.

NOTE for re-recording Ep 3: delete this file before the on-camera shot of
the agent authoring it. After recording, restore from git.

Usage:
    python scripts/python/promote.py
    python scripts/python/promote.py --tracker TrackerA   # subset
    python scripts/python/promote.py --dry-run            # preview
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = REPO_ROOT / "datamodel" / "mappings" / "unified_mapping.yaml"

# ---------------------------------------------------------------------------
# Env-side picklist option-set values (org40ae6a46).
# Re-discover via the EntityDefinitions metadata if you rebuild in a new env.
# ---------------------------------------------------------------------------

TASK_STATUS = {
    "NotStarted": 10600301,
    "InProgress": 10600302,
    "Blocked":    10600303,
    "Done":       10600304,
}

MILESTONE_STATUS = {
    "Planned":    10600201,
    "NotStarted": 10600201,  # alias
    "InProgress": 10600202,
    "OnTrack":    10600202,  # tracker E "OnTrack" → InProgress
    "AtRisk":     10600203,
    "Done":       10600204,
    "Complete":   10600204,
    "Blocked":    10600205,
    "Delayed":    10600205,  # tracker E "Delayed" → Blocked
}

TASK_PRIORITY = {
    "Critical": 10600401,
    "High":     10600402,
    "Medium":   10600403,
    "Low":      10600404,
}

TASK_CATEGORY = {
    "Engineering":   10600501,
    "Marketing":     10600502,
    "Legal":         10600503,
    "Operations":    10600504,
    "Planning":      10600505,
    "Documentation": 10600506,
    "Localization":  10600507,
    "Tooling":       10600508,
}

TASK_SOURCETRACKER = {
    "TrackerA": 10600701,
    "TrackerB": 10600702,
    "TrackerD": 10600703,
}

# ---------------------------------------------------------------------------
# Topology lookups.
# ---------------------------------------------------------------------------

PRIMARY_KEY = {
    "lc_task":      "lc_taskid",
    "lc_milestone": "lc_milestoneid",
}

ENTITY_SET = {
    "lc_stg_tracker_a": "lc_stg_tracker_as",
    "lc_stg_tracker_b": "lc_stg_tracker_bs",
    "lc_stg_tracker_c": "lc_stg_tracker_cs",
    "lc_stg_tracker_d": "lc_stg_tracker_ds",
    "lc_stg_tracker_e": "lc_stg_tracker_es",
}


def _to_iso_date(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        return v[:10] if v else None
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        return None


_CALENDAR_Q_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
_FISCAL_Q_OFFSET = {1: ("09-30", -1), 2: ("12-31", -1),
                    3: ("03-31", 0),  4: ("06-30", 0)}


def _quarter_to_date(q: str | None) -> str | None:
    if not q or not isinstance(q, str):
        return None
    q = q.strip().upper()
    m = re.match(r"^(\d{4})Q([1-4])$", q)
    if m:
        year, qn = int(m.group(1)), int(m.group(2))
        return f"{year}-{_CALENDAR_Q_END[qn]}"
    m = re.match(r"^Q([1-4])FY(\d{2})$", q)
    if m:
        qn = int(m.group(1))
        fy = 2000 + int(m.group(2))
        suffix, year_off = _FISCAL_Q_OFFSET[qn]
        return f"{fy + year_off}-{suffix}"
    return None


def _release_to_quarter(release: str | None) -> str | None:
    if not release or not isinstance(release, str):
        return None
    m = re.search(r"(\d{4}Q[1-4])", release.upper())
    return m.group(1) if m else None


def _email_local(email: str | None) -> str | None:
    if not email or not isinstance(email, str) or "@" not in email:
        return None
    return email.split("@", 1)[0].strip().lower()


def _resolve_assignee(email: str | None, ctx: dict) -> str | None:
    local = _email_local(email)
    return ctx.get("email_to_guid", {}).get(local) if local else None


def _resolve_milestone(hint: str | None, ctx: dict) -> str | None:
    if not hint or not isinstance(hint, str):
        return None
    h = hint.strip().lower()
    if not h:
        return None
    by_name = ctx.get("milestones_by_name") or {}
    if h in by_name:
        return by_name[h]
    for name_lower, mid in by_name.items():
        if name_lower.startswith(h) or h in name_lower:
            return mid
    return None


def _str_status(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, float) and pd.isna(v):
        return None
    return str(v).strip() or None


# ---------------------------------------------------------------------------
# Recipes — each builds the upsert payload for one staging row.
# ---------------------------------------------------------------------------

def recipe_tracker_a(row: dict, ctx: dict) -> dict:
    status_name = _str_status(row.get("lc_status"))
    status_int = TASK_STATUS.get(status_name) if status_name else None
    body: dict[str, Any] = {
        "lc_title":      row.get("lc_title"),
        "lc_notes":      row.get("lc_notes"),
        "lc_duedate":    _to_iso_date(row.get("lc_duedate")),
        "lc_taskstatus": status_int,
        "lc_priority":   TASK_PRIORITY.get(_str_status(row.get("lc_priority"))),
        "lc_sourcetracker": TASK_SOURCETRACKER["TrackerA"],
    }
    if status_int == TASK_STATUS["Blocked"]:
        body["lc_isblocked"] = True
        body["lc_blockerreason"] = row.get("lc_notes") or "(no detail in source)"
    assignee = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if assignee:
        body["lc_assignedtoid@odata.bind"] = f"/lc_teammembers({assignee})"
    mid = _resolve_milestone(row.get("lc_milestonename"), ctx)
    if mid:
        body["lc_milestoneid@odata.bind"] = f"/lc_milestones({mid})"
    if ctx.get("launch_id"):
        body["lc_launchid@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    return body


def recipe_tracker_b(row: dict, ctx: dict) -> dict:
    status_name = _str_status(row.get("lc_status"))
    status_int = TASK_STATUS.get(status_name) if status_name else None
    cat_raw = _str_status(row.get("lc_category"))
    body: dict[str, Any] = {
        # Tracker B's primary on env is lc_name, not lc_title.
        "lc_title":      row.get("lc_name"),
        "lc_duedate":    _to_iso_date(row.get("lc_duedate")),
        "lc_taskstatus": status_int,
        "lc_priority":   TASK_PRIORITY.get(_str_status(row.get("lc_priority"))),
        "lc_category":   TASK_CATEGORY.get(cat_raw),
        "lc_sourcetracker": TASK_SOURCETRACKER["TrackerB"],
    }
    if status_int == TASK_STATUS["Blocked"]:
        body["lc_isblocked"] = True
        body["lc_blockerreason"] = f"[{cat_raw}] (no detail in source)" if cat_raw else "(no detail in source)"
    assignee = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if assignee:
        body["lc_assignedtoid@odata.bind"] = f"/lc_teammembers({assignee})"
    mid = _resolve_milestone(row.get("lc_milestonename"), ctx)
    if mid:
        body["lc_milestoneid@odata.bind"] = f"/lc_milestones({mid})"
    if ctx.get("launch_id"):
        body["lc_launchid@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    return body


def recipe_tracker_c(row: dict, ctx: dict) -> dict:
    body: dict[str, Any] = {
        "lc_name":             row.get("lc_initiative"),
        "lc_milestonestatus":  MILESTONE_STATUS.get(_str_status(row.get("lc_status"))),
        "lc_duedate":          _quarter_to_date(_str_status(row.get("lc_quarter"))),
        "lc_quarter":          _str_status(row.get("lc_quarter")),
    }
    if ctx.get("launch_id"):
        body["lc_launchid@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    owner = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if owner:
        body["lc_ownerid@odata.bind"] = f"/lc_teammembers({owner})"
    return body


def recipe_tracker_d(row: dict, ctx: dict) -> dict:
    body: dict[str, Any] = {
        "lc_title":      row.get("lc_tool"),
        "lc_notes":      row.get("lc_notes"),
        # Tracker D has no status column — default NotStarted.
        "lc_taskstatus": TASK_STATUS["NotStarted"],
        "lc_priority":   TASK_PRIORITY.get(_str_status(row.get("lc_priority"))),
        "lc_category":   TASK_CATEGORY["Tooling"],
        "lc_sourcetracker": TASK_SOURCETRACKER["TrackerD"],
    }
    assignee = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if assignee:
        body["lc_assignedtoid@odata.bind"] = f"/lc_teammembers({assignee})"
    mid = _resolve_milestone(row.get("lc_milestonename"), ctx)
    if mid:
        body["lc_milestoneid@odata.bind"] = f"/lc_milestones({mid})"
    if ctx.get("launch_id"):
        body["lc_launchid@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    return body


def recipe_tracker_e(row: dict, ctx: dict) -> dict:
    project = row.get("lc_project") or ""
    release = row.get("lc_release")
    name = f"{project} ({release})" if release else project
    body: dict[str, Any] = {
        "lc_name":             name or None,
        "lc_milestonestatus":  MILESTONE_STATUS.get(_str_status(row.get("lc_status"))),
        "lc_duedate":          _quarter_to_date(_release_to_quarter(release) or _str_status(release)),
    }
    if ctx.get("launch_id"):
        body["lc_launchid@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    owner = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if owner:
        body["lc_ownerid@odata.bind"] = f"/lc_teammembers({owner})"
    return body


# ---------------------------------------------------------------------------
# Topology — single source of truth.
# ---------------------------------------------------------------------------

class TrackerCfg:
    def __init__(self, source_table, target, lookup_field, select, recipe):
        self.source_table = source_table
        self.target = target
        self.lookup_field = lookup_field  # nav-property name (lowercase in this env)
        self.select = select
        self.recipe = recipe

    @property
    def lookup_value_attr(self) -> str:
        return f"_{self.lookup_field.lower()}_value"

    @property
    def source_entity_set(self) -> str:
        return ENTITY_SET[self.source_table]


_COMMON_PROV = ["lc_sourceid", "lc_sourcefile", "lc_ingestedat", "modifiedon"]

TRACKERS: dict[str, TrackerCfg] = {
    "TrackerA": TrackerCfg(
        source_table="lc_stg_tracker_a",
        target="lc_task",
        lookup_field="lc_sourcestagingaid",
        select=_COMMON_PROV + ["lc_title", "lc_notes", "lc_duedate", "lc_status",
                                "lc_priority", "lc_owneremail", "lc_milestonename"],
        recipe=recipe_tracker_a,
    ),
    "TrackerB": TrackerCfg(
        source_table="lc_stg_tracker_b",
        target="lc_task",
        lookup_field="lc_sourcestagingbid",
        select=_COMMON_PROV + ["lc_name", "lc_category", "lc_duedate", "lc_status",
                                "lc_priority", "lc_owneremail", "lc_milestonename"],
        recipe=recipe_tracker_b,
    ),
    "TrackerC": TrackerCfg(
        source_table="lc_stg_tracker_c",
        target="lc_milestone",
        lookup_field="lc_sourcestagingcid",
        select=_COMMON_PROV + ["lc_initiative", "lc_quarter", "lc_status",
                                "lc_owneremail"],
        recipe=recipe_tracker_c,
    ),
    "TrackerD": TrackerCfg(
        source_table="lc_stg_tracker_d",
        target="lc_task",
        lookup_field="lc_sourcestagingdid",
        select=_COMMON_PROV + ["lc_tool", "lc_notes", "lc_priority",
                                "lc_owneremail", "lc_milestonename"],
        recipe=recipe_tracker_d,
    ),
    "TrackerE": TrackerCfg(
        source_table="lc_stg_tracker_e",
        target="lc_milestone",
        lookup_field="lc_sourcestagingeid",
        select=_COMMON_PROV + ["lc_project", "lc_release", "lc_status",
                                "lc_priority", "lc_owneremail"],
        recipe=recipe_tracker_e,
    ),
}


# ---------------------------------------------------------------------------
# Read + upsert.
# ---------------------------------------------------------------------------

def _read_staging(client: DataverseClient, cfg: TrackerCfg) -> pd.DataFrame:
    df = client.dataframe.get(cfg.source_table, select=cfg.select)
    return df if df is not None else pd.DataFrame()


def _existing_index(client: DataverseClient, cfg: TrackerCfg) -> dict[str, str]:
    """{staging_row_guid (lower) → target_row_guid}, keyed by the back-reference lookup."""
    pk = PRIMARY_KEY[cfg.target]
    lookup_value = cfg.lookup_value_attr
    out: dict[str, str] = {}
    for batch in client.records.get(cfg.target, select=[pk, lookup_value]):
        for rec in batch:
            staging_id = rec.get(lookup_value)
            if staging_id:
                out[str(staging_id).lower()] = rec[pk]
    return out


def _promote_one(
    client: DataverseClient,
    cfg: TrackerCfg,
    ctx: dict,
    dry_run: bool = False,
) -> dict[str, int]:
    df = _read_staging(client, cfg)
    if df.empty:
        return {"read": 0, "deduped": 0, "created": 0, "updated": 0, "skipped": 0}

    raw_count = len(df)

    if "modifiedon" in df.columns:
        df = df.sort_values("modifiedon", ascending=False)
    df = df.drop_duplicates(subset=["lc_sourceid"], keep="first")

    pk_attr = f"{cfg.source_table}id"
    if pk_attr not in df.columns:
        df = client.dataframe.get(cfg.source_table, select=cfg.select + [pk_attr])
        if "modifiedon" in df.columns:
            df = df.sort_values("modifiedon", ascending=False)
        df = df.drop_duplicates(subset=["lc_sourceid"], keep="first")

    existing = _existing_index(client, cfg)

    created = updated = skipped = 0
    for idx, (_, row) in enumerate(df.iterrows()):
        rd = row.to_dict()
        staging_guid = rd.get(pk_attr)
        if not staging_guid:
            skipped += 1
            continue

        body = cfg.recipe(rd, {**ctx, "row_index": idx})
        body = {k: v for k, v in body.items() if v is not None}

        # Bind the back-reference lookup. This IS the upsert key.
        body[f"{cfg.lookup_field}@odata.bind"] = f"/{cfg.source_entity_set}({staging_guid})"

        existing_id = existing.get(str(staging_guid).lower())
        if existing_id:
            if dry_run:
                print(f"      [dry] UPDATE {cfg.target} {existing_id}  ← {cfg.source_table}:{staging_guid}")
            else:
                client.records.update(cfg.target, existing_id, body)
            updated += 1
        else:
            if dry_run:
                print(f"      [dry] CREATE {cfg.target}                  ← {cfg.source_table}:{staging_guid}")
            else:
                new_id = client.records.create(cfg.target, body)
                existing[str(staging_guid).lower()] = new_id
            created += 1

    return {"read": raw_count, "deduped": len(df), "created": created,
            "updated": updated, "skipped": skipped}


def _refresh_milestones(client: DataverseClient, ctx: dict) -> None:
    name_to_id: dict[str, str] = {}
    for batch in client.records.get("lc_milestone", select=["lc_milestoneid", "lc_name"]):
        for rec in batch:
            name = rec.get("lc_name")
            mid = rec.get("lc_milestoneid")
            if name and mid:
                name_to_id[name.strip().lower()] = mid
    ctx["milestones_by_name"] = name_to_id


def _load_context(client: DataverseClient) -> dict:
    launch_id: str | None = None
    launch_name: str | None = None
    for batch in client.records.get("lc_launch", select=["lc_launchid", "lc_name"]):
        for rec in batch:
            launch_id = rec.get("lc_launchid")
            launch_name = rec.get("lc_name")
            break
        if launch_id:
            break

    email_to_guid: dict[str, str] = {}
    for batch in client.records.get("lc_teammember", select=["lc_teammemberid", "lc_email"]):
        for rec in batch:
            local = _email_local(rec.get("lc_email"))
            tid = rec.get("lc_teammemberid")
            if local and tid:
                email_to_guid[local] = tid

    ctx = {
        "launch_id": launch_id,
        "launch_name": launch_name,
        "email_to_guid": email_to_guid,
        "milestones_by_name": {},
    }
    _refresh_milestones(client, ctx)
    return ctx


def _touch_launch(client: DataverseClient, ctx: dict) -> None:
    """No-op write on the launch row to re-fire any prompt-column evaluations.

    Dataverse prompt columns recompute only when a column on the row they
    live on changes — not when *related* rows (milestones, tasks, status
    updates) change. After the migration lands 77 related rows, the
    launch's lc_risksummary prompt column won't re-evaluate on its own.
    Writing the same lc_name back to itself stamps modifiedon, which
    triggers the prompt evaluation pipeline within ~30-60 seconds.
    """
    launch_id = ctx.get("launch_id")
    name = ctx.get("launch_name")
    if not launch_id or not name:
        return
    client.records.update("lc_launch", launch_id, {"lc_name": name})
    print(f"  Touched lc_launch ({name}) to trigger prompt-column refresh.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote staging trackers → unified Launch model")
    parser.add_argument("--tracker", help="Run a single tracker (e.g. TrackerA)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    args = parser.parse_args()

    selected = list(TRACKERS.keys())
    if args.tracker:
        if args.tracker not in TRACKERS:
            print(f"No tracker named {args.tracker}. Options: {', '.join(TRACKERS)}")
            return 2
        selected = [args.tracker]

    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    print(f"Promotion: {len(selected)} tracker(s) → unified model"
          f"{' [dry-run]' if args.dry_run else ''}\n")

    with DataverseClient(url, get_credential()) as client:
        ctx = _load_context(client)
        if not ctx["launch_id"]:
            print("  WARNING: no lc_launch row found — milestones/tasks won't roll up.")
        print(f"  Context: launch_id={ctx['launch_id']}  "
              f"team={len(ctx['email_to_guid'])}  milestones={len(ctx['milestones_by_name'])}\n")

        totals = {"read": 0, "deduped": 0, "created": 0, "updated": 0, "skipped": 0}

        # Milestones first (C, then E) so task trackers can resolve milestone
        # hints against the freshly-promoted set.
        order = ["TrackerC", "TrackerE", "TrackerA", "TrackerB", "TrackerD"]
        order = [t for t in order if t in selected]

        for tracker_name in order:
            cfg = TRACKERS[tracker_name]
            print(f"-> {cfg.source_table}  →  {cfg.target}")
            stats = _promote_one(client, cfg, ctx, dry_run=args.dry_run)
            print(f"    read={stats['read']}  deduped={stats['deduped']}  "
                  f"created={stats['created']}  updated={stats['updated']}  "
                  f"skipped={stats['skipped']}")
            for k in totals:
                totals[k] += stats[k]

            if cfg.target == "lc_milestone" and not args.dry_run:
                _refresh_milestones(client, ctx)

        print("\n=== Promotion complete ===")
        for k, v in totals.items():
            print(f"  rows {k:8s} {v}")
        if args.dry_run:
            print("  (dry-run — no writes performed)")
        else:
            # Touch the launch row last so the lc_risksummary prompt column
            # re-evaluates against the freshly-promoted related rows.
            _touch_launch(client, ctx)

    return 0


if __name__ == "__main__":
    sys.exit(main())
