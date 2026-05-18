"""Five-stop pandas tour over the unified LaunchControl model.

Reads staging (lc_stg_tracker_a..e) and unified (lc_task, lc_milestone,
lc_launch) tables via the Dataverse Python SDK, joins a staging row to
its promoted twin on the back-reference lookup, and finishes with a
provenance pivot counting how many unified rows came from each tracker.

Run twice across promote.py — once before, once after — to see Stop 0
flip from zeros to populated counts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402


STAGING_TABLES = [
    "lc_stg_tracker_a",
    "lc_stg_tracker_b",
    "lc_stg_tracker_c",
    "lc_stg_tracker_d",
    "lc_stg_tracker_e",
]

# (target table, back-reference lookup attribute on the target)
PROVENANCE = [
    ("lc_task",      "_lc_sourcestagingaid_value", "TrackerA"),
    ("lc_task",      "_lc_sourcestagingbid_value", "TrackerB"),
    ("lc_milestone", "_lc_sourcestagingcid_value", "TrackerC"),
    ("lc_task",      "_lc_sourcestagingdid_value", "TrackerD"),
    ("lc_milestone", "_lc_sourcestagingeid_value", "TrackerE"),
]


def _hr(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def stop_0_snapshot(client) -> None:
    _hr("Stop 0 — snapshot: unified row counts")
    rows = []
    for table, pk in [
        ("lc_launch",    "lc_launchid"),
        ("lc_milestone", "lc_milestoneid"),
        ("lc_task",      "lc_taskid"),
    ]:
        df = client.dataframe.get(table, select=[pk])
        rows.append({"table": table, "rows": len(df)})
    snap = pd.DataFrame(rows)
    print(snap.to_string(index=False))
    m = int(snap.loc[snap["table"] == "lc_milestone", "rows"].iloc[0])
    t = int(snap.loc[snap["table"] == "lc_task", "rows"].iloc[0])
    if m == 0 and t == 0:
        print("\nHint: lc_milestone and lc_task are empty — run "
              "`python scripts/python/promote.py` to populate them.")


def stop_1_read_staging(client) -> pd.DataFrame:
    _hr("Stop 1 — read lc_stg_tracker_a as a DataFrame")
    df = client.dataframe.get(
        "lc_stg_tracker_a",
        select=["lc_title", "lc_status", "lc_duedate", "lc_sourcefile"],
    )
    print(f"rows: {len(df)}")
    print(df.head(10).to_string(index=False))
    return df


def stop_2_profile(client) -> None:
    _hr("Stop 2 — row counts across all 5 staging tables")
    rows = []
    for table in STAGING_TABLES:
        df = client.dataframe.get(table, select=["lc_sourcefile"])
        files = df["lc_sourcefile"].dropna().unique().tolist() if "lc_sourcefile" in df.columns else []
        rows.append({
            "table": table,
            "rows": len(df),
            "source_files": ", ".join(sorted(files)) if files else "(none)",
        })
    print(pd.DataFrame(rows).to_string(index=False))


def stop_3_sql_top(client) -> None:
    _hr("Stop 3 — T-SQL TOP query against lc_task")
    # NOTE: client.query.sql() returns a list[Record] (not a DataFrame); use
    # .data on each record and build a DataFrame ourselves.
    # NOTE: client.query.sql() only supports relationship-based JOINs;
    # computed JOIN columns return "No valid link found in JOIN condition".
    # UNION ALL is also not supported — use pd.concat for that.
    sql = (
        "SELECT TOP 5 lc_title, lc_taskstatus, lc_isblocked "
        "FROM lc_task ORDER BY createdon DESC"
    )
    try:
        result = client.query.sql(sql)
        records = [r.data for r in result] if result else []
        df = pd.DataFrame(records)
        if df.empty:
            print("(no rows — lc_task is empty; run promote.py first)")
        else:
            print(df.to_string(index=False))
    except Exception as exc:  # noqa: BLE001
        print(f"skipped — TDS endpoint unavailable ({exc.__class__.__name__}: {exc})")
        print("Stop 3b's pandas merge below carries the join story regardless.")


def stop_3b_merge(client, staging_a: pd.DataFrame) -> None:
    _hr("Stop 3b — pandas merge: staging row ↔ promoted unified twin")
    # Select lookups by their `_value` projection — selecting the bare logical
    # name silently drops the column from the dataframe.
    tasks = client.dataframe.get(
        "lc_task",
        select=[
            "lc_taskid", "lc_title", "lc_taskstatus", "lc_isblocked",
            "_lc_sourcestagingaid_value",
        ],
    )
    if "lc_stg_tracker_aid" not in staging_a.columns:
        staging_a = client.dataframe.get(
            "lc_stg_tracker_a",
            select=["lc_stg_tracker_aid", "lc_title", "lc_status"],
        )

    if "_lc_sourcestagingaid_value" not in tasks.columns:
        print("(lc_task has no _lc_sourcestagingaid_value column — run promote.py first)")
        return

    merged = pd.merge(
        staging_a,
        tasks,
        left_on="lc_stg_tracker_aid",
        right_on="_lc_sourcestagingaid_value",
        how="inner",
        suffixes=("_staging", "_unified"),
    )
    print(f"matched rows: {len(merged)}")
    if not merged.empty:
        cols = [c for c in
                ["lc_title_staging", "lc_status", "lc_title_unified",
                 "lc_taskstatus", "lc_isblocked"]
                if c in merged.columns]
        print(merged[cols].head(10).to_string(index=False))


def stop_4_promoted_view(client) -> None:
    _hr("Stop 4 — unified lc_task view filtered to promoted rows")
    lookup_cols = [
        "_lc_sourcestagingaid_value",
        "_lc_sourcestagingbid_value",
        "_lc_sourcestagingdid_value",
    ]
    df = client.dataframe.get(
        "lc_task",
        select=["lc_title", "lc_taskstatus", "lc_isblocked", *lookup_cols],
    )
    present = [c for c in lookup_cols if c in df.columns]
    if not present:
        print("(no back-reference lookup columns present — run promote.py first)")
        return
    promoted = df[df[present].notna().any(axis=1)]
    print(f"promoted rows: {len(promoted)} / {len(df)}")
    print(promoted[["lc_title", "lc_taskstatus", "lc_isblocked"]].head(10).to_string(index=False))


def stop_5_provenance(client) -> None:
    _hr("Stop 5 — provenance pivot: unified rows per tracker")
    target_selects = {
        "lc_task": [
            "lc_taskid",
            "_lc_sourcestagingaid_value",
            "_lc_sourcestagingbid_value",
            "_lc_sourcestagingdid_value",
        ],
        "lc_milestone": [
            "lc_milestoneid",
            "_lc_sourcestagingcid_value",
            "_lc_sourcestagingeid_value",
        ],
    }
    cache: dict[str, pd.DataFrame] = {}
    rows = []
    for target, lookup_col, label in PROVENANCE:
        if target not in cache:
            cache[target] = client.dataframe.get(target, select=target_selects[target])
        df = cache[target]
        count = int(df[lookup_col].notna().sum()) if lookup_col in df.columns else 0
        rows.append({"tracker": label, "target": target, "promoted_rows": count})
    pivot = pd.DataFrame(rows)
    print(pivot.to_string(index=False))
    print(f"\ntotal promoted rows: {int(pivot['promoted_rows'].sum())}")


def main() -> None:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    with DataverseClient(url, get_credential()) as client:
        stop_0_snapshot(client)
        staging_a = stop_1_read_staging(client)
        stop_2_profile(client)
        stop_3_sql_top(client)
        stop_3b_merge(client, staging_a)
        stop_4_promoted_view(client)
        stop_5_provenance(client)


if __name__ == "__main__":
    main()
