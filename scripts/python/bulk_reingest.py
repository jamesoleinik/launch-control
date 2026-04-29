"""Python bulk re-ingest of all 5 tracker CSVs via the Dataverse SDK.

Faster + more reliable than the per-row CLI loop. Maps choice strings to ints
based on the schema discovered via MCP describe.
"""

from __future__ import annotations

import csv
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = REPO_ROOT / "datamodel" / "samples"

PRIO_A = {"Low": 10600100, "Medium": 10600101, "High": 10600102, "Critical": 10600103}
STAT_A = {"NotStarted": 10600105, "InProgress": 10600106, "Blocked": 10600107, "Done": 10600108}
PRIO_B = {"Low": 10600110, "Medium": 10600111, "High": 10600112, "Critical": 10600113}
STAT_B = {"NotStarted": 10600115, "InProgress": 10600116, "Blocked": 10600117, "Done": 10600118}
STAT_C = {"Planned": 10600125, "InProgress": 10600126, "AtRisk": 10600127, "Done": 10600128}
PRIO_D = {"Low": 10600130, "Medium": 10600131, "High": 10600132, "Critical": 10600133}
PRIO_E = {"Low": 10600140, "Medium": 10600141, "High": 10600142, "Critical": 10600143}
STAT_E = {"OnTrack": 10600145, "AtRisk": 10600146, "Delayed": 10600147, "Done": 10600148}

TRACKERS = [
    {
        "csv": "tracker-a.sample.csv",
        "table": "lc_trackera",
        "fields": [
            ("title", "lc_title", None),
            ("owner", "lc_owneremail", None),
            ("priority", "lc_priority", PRIO_A),
            ("due_date", "lc_duedate", None),
            ("status", "lc_status", STAT_A),
            ("notes", "lc_notes", None),
        ],
    },
    {
        "csv": "tracker-b.sample.csv",
        "table": "lc_trackerb",
        "fields": [
            ("name", "lc_title", None),
            ("owner", "lc_owneremail", None),
            ("category", "lc_category", None),
            ("priority", "lc_priority", PRIO_B),
            ("due_date", "lc_duedate", None),
            ("status", "lc_status", STAT_B),
        ],
    },
    {
        "csv": "tracker-c.sample.csv",
        "table": "lc_trackerc",
        "fields": [
            ("initiative", "lc_initiative", None),
            ("owner", "lc_owneremail", None),
            ("quarter", "lc_quarter", None),
            ("status", "lc_status", STAT_C),
        ],
    },
    {
        "csv": "tracker-d.sample.csv",
        "table": "lc_trackerd",
        "fields": [
            ("tool", "lc_tool", None),
            ("owner", "lc_owneremail", None),
            ("priority", "lc_priority", PRIO_D),
            ("notes", "lc_notes", None),
        ],
    },
    {
        "csv": "tracker-e.sample.csv",
        "table": "lc_trackere",
        "fields": [
            ("project", "lc_project", None),
            ("owner", "lc_owneremail", None),
            ("release", "lc_release", None),
            ("priority", "lc_priority", PRIO_E),
            ("status", "lc_status", STAT_E),
        ],
    },
]


def main() -> int:
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")

    with DataverseClient(env_url, get_credential()) as client:
        run_id = str(uuid.uuid4())
        run_label = f"python-bulk-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        client.records.create(
            "lc_importrun",
            {
                "lc_importrunid": run_id,
                "lc_name": run_label,
                "lc_status": 10600051,  # Running
                "lc_startedat": datetime.now(timezone.utc).date().isoformat(),
            },
        )
        print(f"ImportRun: {run_label}  ({run_id})")

        total = 0
        for spec in TRACKERS:
            csv_path = SAMPLES / spec["csv"]
            with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
                rows_in = list(csv.DictReader(fh))

            sf_id = str(uuid.uuid4())
            client.records.create(
                "lc_sourcefile",
                {
                    "lc_sourcefileid": sf_id,
                    "lc_name": spec["csv"],
                    "lc_filename": spec["csv"],
                    "lc_rowcount": len(rows_in),
                    "lc_ImportRunId@odata.bind": f"/lc_importruns({run_id})",
                },
            )

            print(f"  {spec['table']}: inserting {len(rows_in)} rows...", end=" ", flush=True)
            for row in rows_in:
                rec = {
                    "lc_sourcerowid": str(row["id"]),
                    "lc_sourcesystem": spec["csv"],
                    "lc_sourcefilename": spec["csv"],
                    "lc_ImportRunId@odata.bind": f"/lc_importruns({run_id})",
                }
                for src_col, dv_col, choice_map in spec["fields"]:
                    val = row.get(src_col)
                    if val in (None, ""):
                        continue
                    if choice_map:
                        if val not in choice_map:
                            print(f"\n    WARN: unknown choice '{val}' for {dv_col} in row {row['id']}")
                            continue
                        rec[dv_col] = choice_map[val]
                    else:
                        rec[dv_col] = val
                client.records.create(spec["table"], rec)
            total += len(rows_in)
            print("done")

        client.records.update(
            "lc_importrun",
            run_id,
            {
                "lc_recordsprocessed": total,
                "lc_status": 10600052,  # Succeeded
            },
        )
        print(f"\nIngested {total} rows under run {run_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
