"""Episode 1 seed: insert sanitized rows from samples into staging tables.

Workflow:
  1. Create an lc_ImportRun record (Status=Running).
  2. For each mapping in unified_mapping.yaml, read the corresponding
     datamodel/samples/*.sample.csv and create one staging row per CSV row
     with full provenance (source system, filename, row hash, lc_ImportRun lookup).
  3. Mark lc_ImportRun as Succeeded with a final RecordsProcessed count.

Output: a sanitized copy of each CSV is written to datamodel/seed-data/ so the
public repo has a reproducible seed corpus distinct from the modeling samples.

Usage:
    python launch-control/scripts/seed_data.py
"""

from __future__ import annotations

import csv
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = REPO_ROOT / "datamodel" / "mappings" / "unified_mapping.yaml"
SAMPLES_DIR = REPO_ROOT / "datamodel" / "samples"
SEED_OUT_DIR = REPO_ROOT / "datamodel" / "seed-data"

PREFIX = "lc"
SOURCE_SYSTEM = "EpisodeOneSeed"

# Mirror of CHOICE_BASE in modeling_skill.py — must stay in sync.
CHOICE_BASE = {
    "lc_TrackerA": 10600100,
    "lc_TrackerB": 10600110,
    "lc_TrackerC": 10600120,
    "lc_TrackerD": 10600130,
    "lc_TrackerE": 10600140,
}

IMPORT_RUN_STATUS = {
    "Pending":   10600050,
    "Running":   10600051,
    "Succeeded": 10600052,
    "Failed":    10600053,
}


def _entity_set(logical: str) -> str:
    """Approximate OData entity set name for lookup binding.
    Dataverse usually pluralizes by appending 's'. Existing seed scripts in
    this repo use exactly this convention."""
    return logical + "s"


def _choice_value(table_schema: str, field_schema: str, label: str, options: list[str]) -> int | None:
    """Resolve a string label to its option-set integer using the same scheme
    as modeling_skill.py. Returns None if label is empty or unknown."""
    if not label:
        return None
    base = CHOICE_BASE[table_schema]
    field_offset = 5 if field_schema.endswith("_Status") else 0
    try:
        return base + field_offset + options.index(label)
    except ValueError:
        return None


def _row_hash(row: dict) -> str:
    payload = "|".join(f"{k}={row[k]}" for k in sorted(row))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _build_record(
    mapping: dict,
    row: dict,
    import_run_id: str,
    filename: str,
) -> dict:
    """Translate a CSV row into a Dataverse record payload."""
    table = mapping["target_entity"]
    base = CHOICE_BASE[table]
    payload: dict[str, Any] = {}

    for src_col, spec in mapping["fields"].items():
        schema = spec["schema"].lower()
        ctype = spec["type"]
        raw = (row.get(src_col) or "").strip()
        if raw == "":
            continue
        if ctype == "choice":
            opts = spec.get("options", [])
            field_offset = 5 if spec["schema"].endswith("_Status") else 0
            try:
                idx = opts.index(raw)
                payload[schema] = base + field_offset + idx
            except ValueError:
                # Unknown label — leave blank, mark for review below.
                payload[f"{PREFIX}_needsmanualreview"] = True
        elif ctype in ("integer",):
            payload[schema] = int(raw)
        elif ctype in ("decimal",):
            payload[schema] = float(raw)
        elif ctype == "boolean":
            payload[schema] = raw.lower() in ("true", "1", "yes", "y")
        elif ctype in ("date", "datetime"):
            payload[schema] = raw  # Dataverse accepts ISO 8601 strings.
        else:
            payload[schema] = raw

    # Provenance
    payload[f"{PREFIX}_sourcesystem"] = SOURCE_SYSTEM
    payload[f"{PREFIX}_sourcefilename"] = filename
    payload[f"{PREFIX}_sourcerowhash"] = _row_hash(row)
    payload.setdefault(f"{PREFIX}_needsmanualreview", False)
    payload[f"{PREFIX}_ImportRunId@odata.bind"] = f"/{_entity_set(PREFIX + '_importrun')}({import_run_id})"
    return payload


def main() -> int:
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    credential = get_credential()

    if not MAPPING_PATH.exists():
        print(f"ERROR: mapping not found at {MAPPING_PATH}")
        return 1

    with MAPPING_PATH.open("r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)

    mappings = [m for m in doc.get("mappings", []) if m.get("fields")]
    SEED_OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Seeding {len(mappings)} staging tables in {env_url}")

    with DataverseClient(env_url, credential) as client:
        # 1. Create lc_ImportRun (Running).
        run_name = f"Ep1 seed @ {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
        print(f"\nCreating lc_ImportRun: {run_name}")
        import_run_id = client.records.create(
            f"{PREFIX}_importrun",
            {
                f"{PREFIX}_name": run_name,
                f"{PREFIX}_startedat": datetime.now(timezone.utc).isoformat(),
                f"{PREFIX}_status": IMPORT_RUN_STATUS["Running"],
                f"{PREFIX}_recordsprocessed": 0,
                f"{PREFIX}_notes": f"Seed run from {SOURCE_SYSTEM} via scripts/seed_data.py",
            },
        )
        print(f"  Created lc_ImportRun: {import_run_id}")

        total_rows = 0
        per_table_failures = 0

        # 2. For each mapping, read CSV and insert rows.
        for m in mappings:
            table = m["target_entity"]
            csv_path = SAMPLES_DIR / m["source"]
            if not csv_path.exists():
                print(f"  SKIP {table}: missing {csv_path}")
                continue
            print(f"\n{table} <- {m['source']}")

            with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))

            seed_rows: list[dict] = []
            payloads: list[dict] = []
            for row in rows:
                payloads.append(_build_record(m, row, import_run_id, m["source"]))
                seed_rows.append(row)

            inserted = 0
            try:
                # Bulk insert via CreateMultiple under the hood.
                client.records.create(table.lower(), payloads)
                inserted = len(payloads)
            except Exception as bulk_err:
                # Fall back to per-row so one bad row doesn't sink the batch.
                print(f"  Bulk insert failed ({bulk_err.__class__.__name__}); falling back to per-row.")
                inserted = 0
                seed_rows = []
                for row, payload in zip(rows, payloads):
                    try:
                        client.records.create(table.lower(), payload)
                        inserted += 1
                        seed_rows.append(row)
                    except Exception as e:
                        per_table_failures += 1
                        print(f"  ERROR inserting row {row.get('id')}: {e}")
            total_rows += inserted
            print(f"  Inserted {inserted}/{len(rows)} row(s)")

            # Persist a sanitized seed copy alongside the originals.
            out = SEED_OUT_DIR / m["source"].replace(".sample.csv", ".seed.csv")
            if seed_rows:
                with out.open("w", encoding="utf-8", newline="") as outfh:
                    writer = csv.DictWriter(outfh, fieldnames=list(seed_rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(seed_rows)
                print(f"  Wrote seed copy: {out.relative_to(REPO_ROOT)}")

        # 3. Finalize lc_ImportRun.
        final_status = "Succeeded" if per_table_failures == 0 else "Failed"
        client.records.update(
            f"{PREFIX}_importrun",
            import_run_id,
            {
                f"{PREFIX}_status": IMPORT_RUN_STATUS[final_status],
                f"{PREFIX}_recordsprocessed": total_rows,
                f"{PREFIX}_notes": (
                    f"Seed run completed. status={final_status}, "
                    f"records={total_rows}, failures={per_table_failures}"
                ),
            },
        )
        print(f"\n=== Seed complete ===")
        print(f"lc_ImportRun {import_run_id} -> {final_status}")
        print(f"Records inserted: {total_rows} (failures: {per_table_failures})")

    return 0 if per_table_failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
