"""Episode 3 demo — pandas DataFrame tour over the unified Launch model.

Five short stops:
    1. dataframe.get()      — read a staging table directly into a DataFrame
    2. row-count profile    — across all 5 lc_stg_tracker_* tables
    3. query.sql()          — T-SQL TOP/ORDER BY against the unified lc_task,
                              then a pandas merge across staging + unified
                              (showcasing the SDK's TWO query surfaces)
    4. dataframe.get()      — round-trip lc_task, filtered to promoted rows
    5. provenance pivot     — count promoted rows per source tracker

Run AFTER promote.py has populated lc_task / lc_milestone.

NOTE for re-recording Ep 3: delete this file before the on-camera shot of
the agent authoring it. After recording, restore from git.

Usage:
    python scripts/python/dataframe_tour.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402

from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

STAGING = [
    "lc_stg_tracker_a",
    "lc_stg_tracker_b",
    "lc_stg_tracker_c",
    "lc_stg_tracker_d",
    "lc_stg_tracker_e",
]

# Map source-staging lookup columns on each unified table → which tracker
# they came from. Used by Stop 5's provenance pivot.
PROV_LOOKUPS = {
    "lc_task": {
        "_lc_sourcestagingaid_value": "TrackerA",
        "_lc_sourcestagingbid_value": "TrackerB",
        "_lc_sourcestagingdid_value": "TrackerD",
    },
    "lc_milestone": {
        "_lc_sourcestagingcid_value": "TrackerC",
        "_lc_sourcestagingeid_value": "TrackerE",
    },
}


def _client() -> DataverseClient:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    return DataverseClient(url, get_credential())


def stop_1_read_one_table(client: DataverseClient) -> None:
    print("\n--- Stop 1: dataframe.get('lc_stg_tracker_a') ---")
    df = client.dataframe.get(
        "lc_stg_tracker_a",
        select=["lc_title", "lc_status", "lc_duedate", "lc_sourcefile"],
    )
    print(df.head(10).to_string(index=False))
    print(f"  shape={df.shape}  dtypes={ {k: str(v) for k, v in df.dtypes.items()} }")


def stop_2_profile_all_staging(client: DataverseClient) -> None:
    print("\n--- Stop 2: row-count profile across all 5 staging tables ---")
    rows = []
    for table in STAGING:
        df = client.dataframe.get(table, select=["lc_sourcefile"])
        rows.append({"staging_table": table, "rows": len(df)})
    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    print(f"  total staging rows: {summary['rows'].sum()}")


def stop_3_join_via_sql(client: DataverseClient) -> None:
    print("\n--- Stop 3: query.sql() — top tasks via T-SQL TOP/ORDER BY ---")
    sql = """
        SELECT TOP 5 lc_title, lc_taskstatus, lc_isblocked
          FROM lc_task
         ORDER BY createdon DESC
    """
    try:
        rows = client.query.sql(sql)
        df = pd.DataFrame(rows) if not isinstance(rows, pd.DataFrame) else rows
        print(df.to_string(index=False))
    except Exception as exc:
        # query.sql() requires the TDS endpoint (Dataverse SQL) to be enabled.
        # If it's off, the pandas merge below still demonstrates the analytics
        # angle — call out the limitation honestly.
        print(f"  (query.sql unavailable: {exc.__class__.__name__})")
        print("  Skipping T-SQL stop; pandas merge below covers the join story.")

    print("\n--- Stop 3b: pandas merge — staging row + promoted task row ---")
    staging = client.dataframe.get(
        "lc_stg_tracker_a",
        select=["lc_stg_tracker_aid", "lc_title", "lc_sourceid"],
    )
    tasks = client.dataframe.get(
        "lc_task",
        select=["lc_title", "lc_taskstatus", "_lc_sourcestagingaid_value"],
    )
    # The lookup IS the join key — no string-key gymnastics needed.
    merged = staging.merge(
        tasks,
        left_on="lc_stg_tracker_aid",
        right_on="_lc_sourcestagingaid_value",
        suffixes=("_staging", "_unified"),
    )
    if not merged.empty:
        print(merged[["lc_sourceid", "lc_title_staging",
                      "lc_title_unified", "lc_taskstatus"]].head(10)
              .to_string(index=False))
        print(f"  matched: {len(merged)} of {len(staging)} staging rows")
    else:
        print("  (no matches — promote.py probably hasn't run yet)")

    # SDK gotchas worth flagging for viewers:
    # - client.query.sql() only supports relationship-based JOINs.
    #   Joining on a computed expression returns "No valid link found in
    #   JOIN condition" — pandas merge fills exactly that gap.
    # - UNION ALL isn't supported either; use pd.concat.
    # The lookup-based design used here makes both unnecessary for this query.


def stop_4_unified_view(client: DataverseClient) -> None:
    print("\n--- Stop 4: dataframe.get('lc_task') — promoted rows only ---")
    lookups = list(PROV_LOOKUPS["lc_task"].keys())
    df = client.dataframe.get(
        "lc_task",
        select=["lc_title", "lc_taskstatus", "lc_isblocked"] + lookups,
    )
    has_prov = df[lookups].notna().any(axis=1)
    promoted = df[has_prov]
    print(promoted[["lc_title", "lc_taskstatus", "lc_isblocked"]].head(15)
          .to_string(index=False))
    print(f"  promoted rows: {len(promoted)}  /  total task rows: {len(df)}")


def stop_5_provenance_pivot(client: DataverseClient) -> None:
    print("\n--- Stop 5: rows promoted per source tracker (groupby) ---")
    rows = []
    for target, lookups in PROV_LOOKUPS.items():
        select = list(lookups.keys())
        df = client.dataframe.get(target, select=select)
        for lookup_attr, tracker in lookups.items():
            n = int(df[lookup_attr].notna().sum()) if lookup_attr in df.columns else 0
            if n:
                rows.append({"source": tracker, "target": target, "rows": n})
    pivot = pd.DataFrame(rows).sort_values(["target", "source"]) if rows else pd.DataFrame(
        columns=["source", "target", "rows"]
    )
    print(pivot.to_string(index=False))


def main() -> None:
    with _client() as client:
        stop_1_read_one_table(client)
        stop_2_profile_all_staging(client)
        stop_3_join_via_sql(client)
        stop_4_unified_view(client)
        stop_5_provenance_pivot(client)


if __name__ == "__main__":
    main()
