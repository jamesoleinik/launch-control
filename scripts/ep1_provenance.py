"""Episode 1 helper: add provenance support tables (lc_ImportRun, lc_SourceFile) and lookups.

Creates:
- lc_ImportRun: Name, StartedAt, RecordsProcessed, Status, Notes
- lc_SourceFile: Name, Filename, RowCount, Checksum
- Lookup fields from core tables to lc_ImportRun

Usage: python ep1_provenance.py
Requires: DATAVERSE_URL in .env and scripts/auth.get_credential available (same auth flow as create_datamodel.py)
"""

import os
import sys
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from PowerPlatform.Dataverse.client import DataverseClient


class ImportRunStatus(Enum):
    Pending = 10600050
    Running = 10600051
    Succeeded = 10600052
    Failed = 10600053


def _is_duplicate(e):
    msg = str(e).lower()
    return any(x in msg for x in ["duplicate", "already exists", "matching key", "already being used", "cannot be used again"])


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    prefix = "lc"
    solution_name = "LaunchControl"

    with DataverseClient(env_url, credential) as client:
        # 1. lc_ImportRun
        print("Creating lc_ImportRun table (if missing)...")
        try:
            client.tables.create(
                f"{prefix}_ImportRun",
                {
                    f"{prefix}_StartedAt": "datetime",
                    f"{prefix}_RecordsProcessed": "integer",
                    f"{prefix}_Status": ImportRunStatus,
                    f"{prefix}_Notes": "memo",
                },
                solution=solution_name,
                primary_column=f"{prefix}_Name",
            )
            print("  Created: lc_ImportRun")
        except Exception as e:
            if _is_duplicate(e):
                print("  lc_ImportRun already exists, skipping.")
            else:
                raise

        # 2. lc_SourceFile
        print("Creating lc_SourceFile table (if missing)...")
        try:
            client.tables.create(
                f"{prefix}_SourceFile",
                {
                    f"{prefix}_Filename": "string",
                    f"{prefix}_RowCount": "integer",
                    f"{prefix}_Checksum": "string",
                },
                solution=solution_name,
                primary_column=f"{prefix}_Name",
            )
            print("  Created: lc_SourceFile")
        except Exception as e:
            if _is_duplicate(e):
                print("  lc_SourceFile already exists, skipping.")
            else:
                raise

        # 3. Add lookup fields from core tables to lc_ImportRun
        print("Creating lookup fields to lc_ImportRun (if missing)...")
        # Use lowercase logical names — the lookup API resolves entities by
        # logical name (always lowercase), not by schema name.
        references = [
            (f"{prefix}_launch",       f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_milestone",    f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_task",         f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_statusupdate", f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_teammember",   f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_sourcefile",   f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
        ]

        for ref_table, lookup_name, target_table, display in references:
            try:
                client.tables.create_lookup_field(
                    ref_table,
                    lookup_name,
                    target_table,
                    display_name=display,
                    solution=solution_name,
                )
                print(f"  {ref_table} -> {target_table} ({display})")
            except Exception as e:
                if _is_duplicate(e):
                    print(f"  {ref_table} -> {target_table} already exists, skipping.")
                else:
                    print(f"  Error creating lookup {ref_table} -> {target_table}: {e}")

        print("\nDone. Run pac solution import/pack or use the create_datamodel.py flow to include these tables in an exported solution if you need an explicit solution package.")


if __name__ == "__main__":
    main()
