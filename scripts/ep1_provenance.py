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
from scripts._resilient import attempt_many
from PowerPlatform.Dataverse.client import DataverseClient


class ImportRunStatus(Enum):
    Pending = 10600050
    Running = 10600051
    Succeeded = 10600052
    Failed = 10600053


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()
    prefix = "lc"
    solution_name = "LaunchControl"

    with DataverseClient(env_url, credential) as client:
        # 1+2. Create lc_ImportRun and lc_SourceFile in parallel.
        print("Creating lc_ImportRun + lc_SourceFile in parallel...")
        attempt_many([
            (
                f"{prefix}_ImportRun",
                lambda: client.tables.create(
                    f"{prefix}_ImportRun",
                    {
                        f"{prefix}_StartedAt": "datetime",
                        f"{prefix}_RecordsProcessed": "integer",
                        f"{prefix}_Status": ImportRunStatus,
                        f"{prefix}_Notes": "memo",
                    },
                    solution=solution_name,
                    primary_column=f"{prefix}_Name",
                ),
            ),
            (
                f"{prefix}_SourceFile",
                lambda: client.tables.create(
                    f"{prefix}_SourceFile",
                    {
                        f"{prefix}_Filename": "string",
                        f"{prefix}_RowCount": "integer",
                        f"{prefix}_Checksum": "string",
                    },
                    solution=solution_name,
                    primary_column=f"{prefix}_Name",
                ),
            ),
        ], workers=2)

        # 3. Add lookup fields from core tables to lc_ImportRun -- serialized.
        # Parallel adds collide on the EntityCustomization lock held by the
        # shared target (lc_importrun); serial is reliably faster than
        # parallel-with-retry for this step.
        print("Creating lookup fields to lc_ImportRun (serialized)...")
        # Use lowercase logical names -- the lookup API resolves entities by
        # logical name (always lowercase), not by schema name.
        references = [
            (f"{prefix}_launch",       f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_milestone",    f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_task",         f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_statusupdate", f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_teammember",   f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
            (f"{prefix}_sourcefile",   f"{prefix}_ImportRunId", f"{prefix}_importrun", "Import Run"),
        ]

        attempt_many(
            [
                (
                    f"{ref_table} -> {target_table}",
                    lambda r=ref_table, n=lookup_name, t=target_table, d=display: client.tables.create_lookup_field(
                        r, n, t, display_name=d, solution=solution_name,
                    ),
                )
                for ref_table, lookup_name, target_table, display in references
            ],
            workers=1,
        )

        print("\nDone. Run pac solution import/pack or use the create_datamodel.py flow to include these tables in an exported solution if you need an explicit solution package.")


if __name__ == "__main__":
    main()
