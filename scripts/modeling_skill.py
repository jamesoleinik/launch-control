"""Episode 1 Modeling Skill — generate Dataverse staging tables from sanitized trackers.

Reads:
    datamodel/mappings/unified_mapping.yaml   (schema source of truth)
    datamodel/samples/*.sample.csv            (placeholder schemas; not read here)

Creates one staging table per tracker (lc_TrackerA..lc_TrackerE), each with:
  - Mapped columns from the YAML (typed: string/memo/integer/decimal/datetime/
    date/boolean/choice).
  - Provenance fields: lc_SourceSystem, lc_SourceFilename, lc_SourceRowHash,
    lc_NeedsManualReview.
  - Lookup to lc_ImportRun (created by ep1_provenance.py).

Run AFTER scripts/create_datamodel.py and scripts/ep1_provenance.py.

Usage:
    python launch-control/scripts/modeling_skill.py
"""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = REPO_ROOT / "datamodel" / "mappings" / "unified_mapping.yaml"

SOLUTION = "LaunchControl"
PREFIX = "lc"

# Option-set value ranges (avoid collision with create_datamodel.py: 10600001-49,
# ep1_provenance.py: 10600050-53). Each tracker gets a 10-value block.
CHOICE_BASE = {
    "lc_TrackerA": 10600100,
    "lc_TrackerB": 10600110,
    "lc_TrackerC": 10600120,
    "lc_TrackerD": 10600130,
    "lc_TrackerE": 10600140,
}


def _is_duplicate(e: Exception) -> bool:
    msg = str(e).lower()
    return any(
        x in msg
        for x in [
            "duplicate", "already exists", "matching key",
            "already being used", "cannot be used again",
        ]
    )


def _build_choice_enum(table_schema: str, field_schema: str, options: list[str]) -> type[Enum]:
    """Build a unique Enum class for a choice column with stable option values."""
    base = CHOICE_BASE[table_schema]
    # Reserve 10 values per choice; if a table has multiple choice fields, offset
    # by 5 per field index so values stay unique across the table.
    # (Each tracker has at most 2 choice fields with up to ~5 options each.)
    field_offset = 0
    if field_schema.endswith("_Status"):
        field_offset = 5
    members = {opt: base + field_offset + i for i, opt in enumerate(options)}
    return Enum(f"{table_schema}_{field_schema}", members)


def _columns_for_mapping(mapping: dict) -> dict:
    """Translate YAML field defs to the SDK columns dict."""
    table_schema = mapping["target_entity"]
    primary = mapping["primary_column"]
    cols: dict = {}
    for src_col, spec in mapping["fields"].items():
        schema = spec["schema"]
        # Skip the primary column — it's set via primary_column= on table create.
        if schema == primary:
            continue
        ctype = spec["type"]
        if ctype == "choice":
            cols[schema] = _build_choice_enum(table_schema, schema, spec["options"])
        elif ctype in ("string", "memo", "integer", "decimal", "datetime", "boolean"):
            cols[schema] = ctype
        elif ctype == "date":
            # SDK exposes datetime; date-only behavior set via column metadata later if needed.
            cols[schema] = "datetime"
        else:
            raise ValueError(f"Unsupported field type '{ctype}' on {table_schema}.{schema}")

    # Provenance fields (uniform across all staging tables).
    cols[f"{PREFIX}_SourceSystem"] = "string"
    cols[f"{PREFIX}_SourceFilename"] = "string"
    cols[f"{PREFIX}_SourceRowHash"] = "string"
    cols[f"{PREFIX}_NeedsManualReview"] = "boolean"
    return cols


def main() -> int:
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()

    if not MAPPING_PATH.exists():
        print(f"ERROR: mapping file not found at {MAPPING_PATH}")
        return 1

    with MAPPING_PATH.open("r", encoding="utf-8") as fh:
        mapping_doc = yaml.safe_load(fh)

    mappings = [m for m in mapping_doc.get("mappings", []) if m.get("fields")]
    if not mappings:
        print("ERROR: no mappings with fields found in unified_mapping.yaml")
        return 1

    print(f"Modeling Skill: applying {len(mappings)} staging tables to {env_url}")
    print(f"Solution: {SOLUTION}, prefix: {PREFIX}\n")

    with DataverseClient(env_url, credential) as client:
        # 1. Create each staging table with columns + provenance.
        for m in mappings:
            table = m["target_entity"]
            primary = m["primary_column"]
            cols = _columns_for_mapping(m)
            print(f"Creating {table} (primary={primary}, columns={len(cols)})...")
            try:
                client.tables.create(
                    table,
                    cols,
                    solution=SOLUTION,
                    primary_column=primary,
                )
                print(f"  Created: {table}")
            except Exception as e:
                if _is_duplicate(e):
                    print(f"  {table} already exists, skipping.")
                else:
                    print(f"  ERROR creating {table}: {e}")

        # 2. Add lc_ImportRun lookup to each staging table.
        # Use lowercase logical names for SDK compatibility.
        print("\nAdding lc_ImportRun lookup to each staging table...")
        target_logical = f"{PREFIX}_importrun"
        for m in mappings:
            ref_logical = m["target_entity"].lower()
            try:
                client.tables.create_lookup_field(
                    ref_logical,
                    f"{PREFIX}_ImportRunId",
                    target_logical,
                    display_name="Import Run",
                    solution=SOLUTION,
                )
                print(f"  {ref_logical} -> {target_logical}")
            except Exception as e:
                if _is_duplicate(e):
                    print(f"  {ref_logical} -> {target_logical} already exists, skipping.")
                else:
                    print(f"  ERROR {ref_logical} -> {target_logical}: {e}")

    print("\n=== Modeling Skill complete ===")
    print(f"Created {len(mappings)} staging tables under solution '{SOLUTION}'.")
    print("Next: run scripts/seed_data.py to insert sanitized seed rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
