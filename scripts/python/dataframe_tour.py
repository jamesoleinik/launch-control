"""Episode 3 demo — pandas DataFrame tour over the unified Launch model.

Five short stops:
    1. dataframe.get()      — read a staging table directly into a DataFrame
    2. groupby + describe   — quick profile across all 5 staging trackers
    3. query_sql()          — cross-table JOIN across staging and unified
    4. dataframe.get()      — round-trip the unified lc_task table
    5. provenance pivot     — count promoted rows per source tracker

Run AFTER promote.py has populated lc_task / lc_milestone with lc_stagingsource.

Usage:
    python launch-control/scripts/python/dataframe_tour.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402

from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

STAGING = ["lc_trackera", "lc_trackerb", "lc_trackerc", "lc_trackerd", "lc_trackere"]


def _client() -> DataverseClient:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    return DataverseClient(url, get_credential())


def stop_1_read_one_table(client: DataverseClient) -> None:
    print("\n--- Stop 1: dataframe.get('lc_trackera') ---")
    df = client.dataframe.get(
        "lc_trackera",
        select=["lc_title", "lc_status", "lc_duedate", "lc_sourcefilename"],
    )
    print(df.to_string(index=False))
    print(f"  shape={df.shape}  dtypes={dict(df.dtypes)}")


def stop_2_profile_all_staging(client: DataverseClient) -> None:
    print("\n--- Stop 2: row-count profile across all 5 staging tables ---")
    rows = []
    for table in STAGING:
        df = client.dataframe.get(table, select=["lc_sourcefilename"])
        rows.append({"staging_table": table, "rows": len(df)})
    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    print(f"  total staging rows: {summary['rows'].sum()}")


def stop_3_join_via_sql(client: DataverseClient) -> None:
    print("\n--- Stop 3: query.sql() — top tasks via T-SQL TOP/ORDER BY ---")
    sql = """
        SELECT TOP 5 lc_title, lc_taskstatus, lc_stagingsource
          FROM lc_task
         ORDER BY lc_stagingsource DESC
    """
    rows = client.query.sql(sql)
    df = pd.DataFrame(rows) if not isinstance(rows, pd.DataFrame) else rows
    print(df.to_string(index=False))

    print("\n--- Stop 3b: pandas merge — staging row + promoted task row ---")
    staging = client.dataframe.get(
        "lc_trackera", select=["lc_sourcerowid", "lc_title", "lc_sourcefilename"]
    )
    tasks = client.dataframe.get(
        "lc_task", select=["lc_title", "lc_taskstatus", "lc_stagingsource"]
    )
    staging = staging.assign(
        provenance=staging["lc_sourcerowid"].map(lambda r: f"lc_trackera:{r}")
    )
    merged = staging.merge(
        tasks, left_on="provenance", right_on="lc_stagingsource",
        suffixes=("_staging", "_unified"),
    )
    print(merged[["lc_title_staging", "lc_title_unified", "lc_taskstatus", "provenance"]]
          .to_string(index=False))


def stop_4_unified_view(client: DataverseClient) -> None:
    print("\n--- Stop 4: dataframe.get('lc_task') — unified task view ---")
    df = client.dataframe.get(
        "lc_task",
        select=["lc_title", "lc_taskstatus", "lc_stagingsource"],
    )
    only_promoted = df[df["lc_stagingsource"].notna()]
    print(only_promoted.to_string(index=False))
    print(f"  promoted rows: {len(only_promoted)}  /  total task rows: {len(df)}")


def stop_5_provenance_pivot(client: DataverseClient) -> None:
    print("\n--- Stop 5: rows promoted per source tracker (groupby) ---")
    task_df = client.dataframe.get("lc_task", select=["lc_stagingsource"])
    ms_df = client.dataframe.get("lc_milestone", select=["lc_stagingsource"])

    def _source(row) -> str | None:
        if row is None or (isinstance(row, float) and pd.isna(row)) or not isinstance(row, str):
            return None
        return row.split(":", 1)[0]

    task_df = task_df.assign(source=task_df["lc_stagingsource"].map(_source))
    ms_df = ms_df.assign(source=ms_df["lc_stagingsource"].map(_source))

    combined = pd.concat(
        [
            task_df.dropna(subset=["source"]).assign(target="lc_task"),
            ms_df.dropna(subset=["source"]).assign(target="lc_milestone"),
        ],
        ignore_index=True,
    )
    pivot = (
        combined.groupby(["source", "target"]).size().reset_index(name="rows")
        if not combined.empty
        else pd.DataFrame(columns=["source", "target", "rows"])
    )
    print(pivot.to_string(index=False))


def main() -> None:
    client = _client()
    stop_1_read_one_table(client)
    stop_2_profile_all_staging(client)
    stop_3_join_via_sql(client)
    stop_4_unified_view(client)
    stop_5_provenance_pivot(client)


if __name__ == "__main__":
    main()
