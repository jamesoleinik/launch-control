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


def recipe_tracker_a(row: dict) -> dict:
    return {
        "lc_title": row.get("lc_title"),
        "lc_description": row.get("lc_notes"),
        "lc_duedate": _to_iso_date(row.get("lc_duedate")),
        "lc_taskstatus": TRACKER_A_STATUS.get(row.get("lc_status")),
    }


def recipe_tracker_b(row: dict) -> dict:
    cat = row.get("lc_category")
    desc = f"[{cat}]" if cat else None
    return {
        "lc_title": row.get("lc_title"),
        "lc_description": desc,
        "lc_duedate": _to_iso_date(row.get("lc_duedate")),
        "lc_taskstatus": TRACKER_B_STATUS.get(row.get("lc_status")),
    }


def recipe_tracker_c(row: dict) -> dict:
    return {
        "lc_name": row.get("lc_initiative"),
        "lc_milestonestatus": TRACKER_C_STATUS.get(row.get("lc_status")),
    }


def recipe_tracker_d(row: dict) -> dict:
    return {
        "lc_title": row.get("lc_tool"),
        "lc_description": row.get("lc_notes"),
        # TrackerD has no status column — default NotStarted so promoted rows
        # are visible on dashboards.
        "lc_taskstatus": TASK_STATUS["NotStarted"],
    }


def recipe_tracker_e(row: dict) -> dict:
    project = row.get("lc_project") or ""
    release = row.get("lc_release")
    name = f"{project} ({release})" if release else project
    return {
        "lc_name": name or None,
        "lc_milestonestatus": TRACKER_E_STATUS.get(row.get("lc_status")),
    }


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
                    "lc_title", "lc_notes", "lc_duedate", "lc_status"],
    "lc_trackerb": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_title", "lc_category", "lc_duedate", "lc_status"],
    "lc_trackerc": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_initiative", "lc_quarter", "lc_status"],
    "lc_trackerd": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_tool", "lc_notes"],
    "lc_trackere": ["lc_sourcerowid", "lc_sourcefilename", "_lc_importrunid_value", "modifiedon",
                    "lc_project", "lc_release", "lc_status"],
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
) -> list[dict]:
    """One payload per staging row, ready for create/update on the unified table."""
    if df_staging.empty:
        return []
    payloads: list[dict] = []
    for _, row in df_staging.iterrows():
        rd = row.to_dict()
        body = recipe(rd)
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

    payloads = _build_payloads(df, source_table, target, recipe)

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

    totals = {"read": 0, "deduped": 0, "created": 0, "updated": 0, "skipped": 0}
    with DataverseClient(env_url, get_credential()) as client:
        # Cache per-target existing-row index.
        existing_cache: dict[str, dict[str, str]] = {}
        for m in mappings:
            source_table = m["target_entity"].lower()
            target = m["promote_to"].lower()
            recipe = RECIPES.get(source_table)
            if not recipe:
                print(f"  {source_table}: no recipe registered, skipping")
                continue

            if target not in existing_cache:
                print(f"  Indexing existing {target} rows by lc_StagingSource...")
                existing_cache[target] = _existing_rows(client, target)
                print(f"    {len(existing_cache[target])} already promoted")

            print(f"\n-> {source_table}  ->  {target}")
            stats = _promote_one(
                client, source_table, target, recipe,
                existing_cache[target], dry_run=args.dry_run,
            )
            print(f"    read={stats['read']}  deduped={stats['deduped']}  "
                  f"created={stats['created']}  updated={stats['updated']}  "
                  f"skipped={stats['skipped']}")
            for k, v in stats.items():
                totals[k] += v

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
