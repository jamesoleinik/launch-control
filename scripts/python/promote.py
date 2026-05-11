"""Episode 3 — Promote staging tracker rows into the unified Launch model.

Reads:
    datamodel/mappings/unified_mapping.yaml   (drives WHERE each tracker row goes)

For every mapping with a `promote_to:` hint:
    1. Pull staging rows from the tracker table (lc_TrackerA..E)
    2. Normalize fields -> unified shape (lc_Task or lc_Milestone)
    3. Map per-tracker status labels onto the target choice values
    4. Compute lc_StagingSource = "<staging_table>:<source_row_id>" — used as the
       upsert key AND a back-reference for provenance
    5. Carry lc_ImportRunId forward so unified rows trace back to the run that
       produced them

Pandas-driven via client.dataframe.{get,create,update}; falls back to
records.upsert / records.create / records.update where the dataframe namespace
needs a primary-key column we don't have at row-build time.

Idempotent: re-running the script promotes any new staging rows and updates
existing unified rows in place.

Run AFTER scripts/python/_add_staging_source.py has added lc_StagingSource to
lc_task and lc_milestone (one-time).

Usage:
    python launch-control/scripts/python/promote.py
    python launch-control/scripts/python/promote.py --tracker TrackerA   # subset
    python launch-control/scripts/python/promote.py --dry-run            # preview
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPING_PATH = REPO_ROOT / "datamodel" / "mappings" / "unified_mapping.yaml"

# ---------------------------------------------------------------------------
# Per-tracker promotion recipes.
#
# Each recipe takes a row dict (keys = source_column names from the YAML) and
# produces a dict of unified-table fields. We keep recipes explicit so the
# normalization logic is auditable for the demo.
# ---------------------------------------------------------------------------

# Target choice values (from EntityDefinitions; see episode notes).
TASK_STATUS = {
    "NotStarted": 10600020,
    "InProgress": 10600021,
    "Done": 10600022,
    "Blocked": 10600023,
}
MILESTONE_STATUS = {
    "NotStarted": 10600010,
    "InProgress": 10600011,
    "Complete": 10600012,
    "AtRisk": 10600013,
    "Blocked": 10600014,
}

# Source-int -> target-int. One map per tracker (status option-set values
# differ per staging table by design — see Ep 1 notes on the 10600100..149
# range allocation).
TRACKER_A_STATUS = {
    10600105: TASK_STATUS["NotStarted"],
    10600106: TASK_STATUS["InProgress"],
    10600107: TASK_STATUS["Blocked"],
    10600108: TASK_STATUS["Done"],
}
TRACKER_B_STATUS = {
    10600115: TASK_STATUS["NotStarted"],
    10600116: TASK_STATUS["InProgress"],
    10600117: TASK_STATUS["Blocked"],
    10600118: TASK_STATUS["Done"],
}
TRACKER_C_STATUS = {
    10600125: MILESTONE_STATUS["NotStarted"],   # Planned
    10600126: MILESTONE_STATUS["InProgress"],
    10600127: MILESTONE_STATUS["AtRisk"],
    10600128: MILESTONE_STATUS["Complete"],     # Done
}
TRACKER_E_STATUS = {
    10600145: MILESTONE_STATUS["InProgress"],   # OnTrack
    10600146: MILESTONE_STATUS["AtRisk"],
    10600147: MILESTONE_STATUS["Blocked"],      # Delayed
    10600148: MILESTONE_STATUS["Complete"],     # Done
}


def _to_iso_date(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, str):
        return v[:10]
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Quarter / release helpers.
#
# Two quarter dialects show up in staging:
#   * Calendar:  "2026Q3"  -> last day of Sep 2026
#   * Fiscal:    "Q1FY27"  -> Microsoft fiscal year (Jul-Jun); Q1FY27 = Jul-Sep
#                              2026 -> 2026-09-30
# Returns None on anything we don't recognize so the recipe can simply omit
# the field rather than poison the unified row with a bogus date.
# ---------------------------------------------------------------------------

_CALENDAR_Q_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
# MSFT fiscal year FY{N} starts July 1 of calendar year N-1.
# Q1FY27 = Jul-Sep 2026, Q2FY27 = Oct-Dec 2026, Q3FY27 = Jan-Mar 2027, Q4FY27 = Apr-Jun 2027.
_FISCAL_Q_OFFSET = {
    1: ("09-30", -1),  # cal year = FY - 1
    2: ("12-31", -1),
    3: ("03-31", 0),
    4: ("06-30", 0),
}


def _quarter_to_date(q: str | None) -> str | None:
    """Translate "2026Q3" or "Q1FY27" to an ISO end-of-quarter date."""
    if not q or not isinstance(q, str):
        return None
    q = q.strip().upper()
    # Calendar: YYYYQN
    m = re.match(r"^(\d{4})Q([1-4])$", q)
    if m:
        year, qn = int(m.group(1)), int(m.group(2))
        return f"{year}-{_CALENDAR_Q_END[qn]}"
    # Fiscal: QNFYYY (2-digit FY) e.g. Q1FY27
    m = re.match(r"^Q([1-4])FY(\d{2})$", q)
    if m:
        qn = int(m.group(1))
        fy = 2000 + int(m.group(2))
        suffix, year_off = _FISCAL_Q_OFFSET[qn]
        return f"{fy + year_off}-{suffix}"
    return None


def _release_to_quarter(release: str | None) -> str | None:
    """Pull the first calendar quarter token (e.g. 2026Q3) out of a release string."""
    if not release or not isinstance(release, str):
        return None
    m = re.search(r"(\d{4}Q[1-4])", release.upper())
    return m.group(1) if m else None


def _email_local(email: str | None) -> str | None:
    """Lowercased local-part of an email, or None. Lets us match across domains
    (staging is @example.com; lc_teammember is @contoso.com)."""
    if not email or not isinstance(email, str) or "@" not in email:
        return None
    return email.split("@", 1)[0].strip().lower()


def _resolve_assignee(email: str | None, ctx: dict) -> str | None:
    """email -> lc_teammemberid GUID, or None if no match."""
    local = _email_local(email)
    if not local:
        return None
    return ctx.get("email_to_guid", {}).get(local)


def _resolve_milestone(hint: str | None, ctx: dict) -> str | None:
    """Resolve a free-text milestone hint to an lc_milestoneid.

    Tracker C milestones use the bare initiative name ("Smart Widget Pro GA").
    Tracker E milestones append a release suffix ("Smart Widget Pro v1.0
    release (2026Q3)"). Match strategy: exact (case-insensitive), then
    case-insensitive prefix. None on no match — caller decides whether to
    leave the task orphaned or assign a default.
    """
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


def recipe_tracker_a(row: dict, ctx: dict) -> dict:
    status = TRACKER_A_STATUS.get(row.get("lc_status"))
    body: dict[str, Any] = {
        "lc_title": row.get("lc_title"),
        "lc_description": row.get("lc_notes"),
        "lc_duedate": _to_iso_date(row.get("lc_duedate")),
        "lc_taskstatus": status,
    }
    if status == TASK_STATUS["Blocked"]:
        body["lc_isblocked"] = True
        body["lc_blockerreason"] = row.get("lc_notes")
    assignee = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if assignee:
        body["lc_AssignedToId@odata.bind"] = f"/lc_teammembers({assignee})"
    mid = _resolve_milestone(row.get("lc_milestone"), ctx)
    if mid:
        body["lc_MilestoneId@odata.bind"] = f"/lc_milestones({mid})"
    return body


def recipe_tracker_b(row: dict, ctx: dict) -> dict:
    cat = row.get("lc_category")
    desc = f"[{cat}]" if cat else None
    status = TRACKER_B_STATUS.get(row.get("lc_status"))
    body: dict[str, Any] = {
        "lc_title": row.get("lc_title"),
        "lc_description": desc,
        "lc_duedate": _to_iso_date(row.get("lc_duedate")),
        "lc_taskstatus": status,
    }
    if status == TASK_STATUS["Blocked"]:
        body["lc_isblocked"] = True
        # TrackerB has no notes column. Best signal we have is the category,
        # which is at least better than NULL on a Blocked task.
        body["lc_blockerreason"] = f"[{cat}] (no detail in source)" if cat else "(no detail in source)"
    assignee = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if assignee:
        body["lc_AssignedToId@odata.bind"] = f"/lc_teammembers({assignee})"
    mid = _resolve_milestone(row.get("lc_milestone"), ctx)
    if mid:
        body["lc_MilestoneId@odata.bind"] = f"/lc_milestones({mid})"
    return body


def recipe_tracker_c(row: dict, ctx: dict) -> dict:
    body: dict[str, Any] = {
        "lc_name": row.get("lc_initiative"),
        "lc_milestonestatus": TRACKER_C_STATUS.get(row.get("lc_status")),
        "lc_duedate": _quarter_to_date(row.get("lc_quarter")),
        "lc_sortorder": _sort_order(row, ctx),
    }
    if ctx.get("launch_id"):
        body["lc_LaunchId@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    # lc_milestone has no AssignedTo lookup — owner info is captured on related tasks instead.
    return body


def recipe_tracker_d(row: dict, ctx: dict) -> dict:
    body: dict[str, Any] = {
        "lc_title": row.get("lc_tool"),
        "lc_description": row.get("lc_notes"),
        # TrackerD has no status column — default NotStarted so promoted rows
        # are visible on dashboards.
        "lc_taskstatus": TASK_STATUS["NotStarted"],
    }
    assignee = _resolve_assignee(row.get("lc_owneremail"), ctx)
    if assignee:
        body["lc_AssignedToId@odata.bind"] = f"/lc_teammembers({assignee})"
    mid = _resolve_milestone(row.get("lc_milestone"), ctx)
    if mid:
        body["lc_MilestoneId@odata.bind"] = f"/lc_milestones({mid})"
    return body


def recipe_tracker_e(row: dict, ctx: dict) -> dict:
    project = row.get("lc_project") or ""
    release = row.get("lc_release")
    name = f"{project} ({release})" if release else project
    body: dict[str, Any] = {
        "lc_name": name or None,
        "lc_milestonestatus": TRACKER_E_STATUS.get(row.get("lc_status")),
        # Release strings can be "2026Q3" itself or "...release (2026Q3)".
        "lc_duedate": _quarter_to_date(_release_to_quarter(release) or release),
        "lc_sortorder": _sort_order(row, ctx),
    }
    if ctx.get("launch_id"):
        body["lc_LaunchId@odata.bind"] = f"/lc_launchs({ctx['launch_id']})"
    # lc_milestone has no AssignedTo lookup — owner info is captured on related tasks instead.
    return body


def _sort_order(row: dict, ctx: dict) -> int | None:
    """Numeric sort key. Prefer staging lc_sourcerowid when it parses as int;
    else fall back to the per-recipe enumerate index from ctx."""
    raw = row.get("lc_sourcerowid")
    if raw is not None:
        try:
            return int(str(raw).strip())
        except (TypeError, ValueError):
            pass
    return ctx.get("row_index")


RECIPES = {
    "lc_trackera": recipe_tracker_a,
    "lc_trackerb": recipe_tracker_b,
    "lc_trackerc": recipe_tracker_c,
    "lc_trackerd": recipe_tracker_d,
    "lc_trackere": recipe_tracker_e,
}


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

PRIMARY_KEY = {"lc_task": "lc_taskid", "lc_milestone": "lc_milestoneid"}

# Per-source-table select list. Only ask for columns that exist on that table.
SELECT_BY_SOURCE = {
    "lc_trackera": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_title", "lc_notes", "lc_duedate", "lc_status", "lc_owneremail", "lc_milestone"],
    "lc_trackerb": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_title", "lc_category", "lc_duedate", "lc_status", "lc_owneremail", "lc_milestone"],
    "lc_trackerc": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_initiative", "lc_quarter", "lc_status", "lc_owneremail"],
    "lc_trackerd": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_tool", "lc_notes", "lc_owneremail", "lc_milestone"],
    "lc_trackere": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_project", "lc_release", "lc_status", "lc_owneremail"],
}


def _existing_rows(client: DataverseClient, target: str) -> dict[str, str]:
    """Return {lc_StagingSource: target_id} for already-promoted rows."""
    pk = PRIMARY_KEY[target]
    out: dict[str, str] = {}
    for batch in client.records.get(target, select=[pk, "lc_stagingsource"]):
        for rec in batch:
            ss = rec.get("lc_stagingsource")
            if ss:
                out[ss] = rec[pk]
    return out


def _read_staging(client: DataverseClient, source_table: str) -> pd.DataFrame:
    """Pull a staging tracker into a DataFrame."""
    df = client.dataframe.get(source_table, select=SELECT_BY_SOURCE[source_table])
    return df if df is not None else pd.DataFrame()


def _build_payloads(
    df_staging: pd.DataFrame,
    source_table: str,
    target: str,
    recipe,
    ctx: dict,
) -> list[dict]:
    """One payload per staging row, ready for create/update on the unified table."""
    if df_staging.empty:
        return []
    payloads: list[dict] = []
    for idx, (_, row) in enumerate(df_staging.iterrows()):
        rd = row.to_dict()
        row_ctx = {**ctx, "row_index": idx}
        body = recipe(rd, row_ctx)
        body["lc_stagingsource"] = f"{source_table}:{rd.get('lc_sourcerowid')}"
        # Forward the ImportRun lookup for provenance.
        run_id = rd.get("_lc_importrunid_value")
        if run_id:
            body["lc_ImportRunId@odata.bind"] = f"/lc_importruns({run_id})"
        # Drop None values so we don't overwrite existing unified data with NULL.
        body = {k: v for k, v in body.items() if v is not None}
        payloads.append(body)
    return payloads


def _promote_one(
    client: DataverseClient,
    source_table: str,
    target: str,
    recipe,
    existing: dict[str, str],
    ctx: dict,
    dry_run: bool = False,
) -> dict[str, int]:
    df = _read_staging(client, source_table)
    if df.empty:
        return {"read": 0, "deduped": 0, "created": 0, "updated": 0, "skipped": 0}

    raw_count = len(df)
    # Last-writer-wins: dedupe by lc_sourcerowid, keep the latest modifiedon.
    # This is "the staging tables are append-only snapshots; the unified
    # table holds one row per logical source-row."
    if "modifiedon" in df.columns:
        df = df.sort_values("modifiedon", ascending=False)
    df = df.drop_duplicates(subset=["lc_sourcerowid"], keep="first")

    payloads = _build_payloads(df, source_table, target, recipe, ctx)

    created = updated = skipped = 0
    for body in payloads:
        ss = body.get("lc_stagingsource")
        if not ss:
            skipped += 1
            continue
        if ss in existing:
            target_id = existing[ss]
            if dry_run:
                print(f"      [dry] UPDATE {target} {target_id} ← {ss}")
            else:
                client.records.update(target, target_id, body)
            updated += 1
        else:
            if dry_run:
                print(f"      [dry] CREATE {target}                ← {ss}")
            else:
                new_id = client.records.create(target, body)
                existing[ss] = new_id
            created += 1
    return {"read": raw_count, "deduped": len(df), "created": created,
            "updated": updated, "skipped": skipped}


def _refresh_milestones(client: DataverseClient, ctx: dict) -> None:
    """(Re)load milestone name->id index into ctx.

    Called once at startup AND after each milestone-promoting tracker so
    task-promoting trackers downstream see the latest milestone set.
    """
    name_to_id: dict[str, str] = {}
    for batch in client.records.get("lc_milestone", select=["lc_milestoneid", "lc_name"]):
        for rec in batch:
            name = rec.get("lc_name")
            mid = rec.get("lc_milestoneid")
            if name and mid:
                name_to_id[name.strip().lower()] = mid
    ctx["milestones_by_name"] = name_to_id


def _load_context(client: DataverseClient) -> dict:
    """Read singleton lookups once: the launch row + email->teammember map.

    The demo has exactly one lc_launch ("Q3 Widget Launch"); every promoted
    milestone rolls up to it. Email keys are normalized to lowercased local-part
    so staging (@example.com) can match teammember rows (@contoso.com)."""
    launch_id: str | None = None
    for batch in client.records.get("lc_launch", select=["lc_launchid", "lc_name"]):
        for rec in batch:
            launch_id = rec.get("lc_launchid")
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

    ctx = {"launch_id": launch_id, "email_to_guid": email_to_guid, "milestones_by_name": {}}
    _refresh_milestones(client, ctx)
    return ctx


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote staging trackers -> unified model")
    parser.add_argument("--tracker", help="Limit to one tracker, e.g. TrackerA")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    args = parser.parse_args()

    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")

    with MAPPING_PATH.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    mappings = [m for m in doc.get("mappings", []) if m.get("promote_to")]
    if args.tracker:
        mappings = [m for m in mappings if m["target_entity"].endswith(args.tracker)]
        if not mappings:
            print(f"No mapping found for {args.tracker}")
            return 1

    print(f"Promotion: {len(mappings)} mapping(s) -> unified model{' [dry-run]' if args.dry_run else ''}\n")

    # Process milestone-promoting trackers first so task trackers can resolve
    # the lc_milestone hint to a real lookup.
    mappings.sort(key=lambda m: 0 if m["promote_to"].lower() == "lc_milestone" else 1)

    totals = {"read": 0, "deduped": 0, "created": 0, "updated": 0, "skipped": 0}
    with DataverseClient(env_url, get_credential()) as client:
        ctx = _load_context(client)
        print(f"  Context: launch_id={ctx['launch_id']}  "
              f"teammembers indexed={len(ctx['email_to_guid'])}  "
              f"milestones indexed={len(ctx['milestones_by_name'])}\n")

        # Cache per-target existing-row index.
        existing_cache: dict[str, dict[str, str]] = {}
        last_target = None
        for m in mappings:
            source_table = m["target_entity"].lower()
            target = m["promote_to"].lower()
            recipe = RECIPES.get(source_table)
            if not recipe:
                print(f"  {source_table}: no recipe registered, skipping")
                continue

            # If we just finished the milestone phase, refresh the milestone
            # index so subsequent task recipes can resolve names.
            if last_target == "lc_milestone" and target != "lc_milestone":
                _refresh_milestones(client, ctx)
                print(f"\n  (refreshed milestone index: {len(ctx['milestones_by_name'])} milestones)\n")

            if target not in existing_cache:
                print(f"  Indexing existing {target} rows by lc_StagingSource...")
                existing_cache[target] = _existing_rows(client, target)
                print(f"    {len(existing_cache[target])} already promoted")

            print(f"\n-> {source_table}  ->  {target}")
            stats = _promote_one(
                client, source_table, target, recipe,
                existing_cache[target], ctx, dry_run=args.dry_run,
            )
            print(f"    read={stats['read']}  deduped={stats['deduped']}  "
                  f"created={stats['created']}  updated={stats['updated']}  "
                  f"skipped={stats['skipped']}")
            for k, v in stats.items():
                totals[k] += v
            last_target = target

    print(f"\n=== Promotion complete ===")
    print(f"  rows read:    {totals['read']}")
    print(f"  after dedup:  {totals['deduped']}")
    print(f"  rows created: {totals['created']}")
    print(f"  rows updated: {totals['updated']}")
    print(f"  rows skipped: {totals['skipped']}")
    if args.dry_run:
        print("  (dry-run — no writes performed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
