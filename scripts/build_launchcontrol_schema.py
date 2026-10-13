"""Build LaunchControl: publisher + solution + tables + lookups.

Design notes:
- Dataverse holds a per-environment EntityCustomization lock around every
  schema change, so this script is strictly serial (no thread pool). It retries
  only the known transient lock conflict and surfaces all other errors.
- Every step is gated by a pre-existence check, so a re-run is essentially a
  no-op (one GET per table/lookup). Safe to re-run for recordings.

Scope:
  --scope unified  (default) -- 5 unified tables + 10 cross-table lookups.
  --scope staging            -- 5 staging tables + 5 provenance lookups
                                (requires unified scope to exist).
  --scope all                -- everything in one go (~12 min wall clock).
"""

import argparse
import os
import sys
import time
from enum import Enum

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, get_token, load_env
from scripts._resilient import short_error
from PowerPlatform.Dataverse.client import DataverseClient

PREFIX = "lc"
SOLUTION = "LaunchControl"
PUBLISHER_UNIQUE = "LaunchControl"
PUBLISHER_PREFIX = "lc"
PUBLISHER_OPTVAL_PREFIX = 10600


class LaunchStatus(Enum):
    OnTrack = 10600101
    AtRisk = 10600102
    Delayed = 10600103
    OnHold = 10600104
    Complete = 10600105


class MilestoneStatus(Enum):
    Planned = 10600201
    InProgress = 10600202
    AtRisk = 10600203
    Done = 10600204
    Blocked = 10600205


class TaskStatus(Enum):
    NotStarted = 10600301
    InProgress = 10600302
    Blocked = 10600303
    Done = 10600304


class Priority(Enum):
    Critical = 10600401
    High = 10600402
    Medium = 10600403
    Low = 10600404


class TaskCategory(Enum):
    Engineering = 10600501
    Marketing = 10600502
    Legal = 10600503
    Operations = 10600504
    Planning = 10600505
    Documentation = 10600506
    Localization = 10600507
    Tooling = 10600508


class Health(Enum):
    Green = 10600601
    Yellow = 10600602
    Red = 10600603


class QualityGateStatus(Enum):
    Pending = 10600801
    Passed = 10600802
    Failed = 10600803
    NeedsReview = 10600804


class SourceTracker(Enum):
    TrackerA = 10600701
    TrackerB = 10600702
    TrackerD = 10600703


def _is_dup(e: BaseException) -> bool:
    m = str(e).lower()
    return any(s in m for s in ("already exists", "duplicate", "is not unique"))


def _is_customization_lock(e: BaseException) -> bool:
    message = str(e).lower()
    return (
        "customizationlockexception" in message
        or "cannot start another [entitycustomization]" in message
    )


def _column_names(client, schema: str) -> set[str]:
    columns = client.tables.list_columns(schema) or []
    return {
        name
        for column in columns
        if (
            name := (
                column.get("LogicalName")
                if isinstance(column, dict)
                else getattr(column, "LogicalName", None)
            )
        )
    }


def _ensure_columns(client, schema: str, columns: dict) -> None:
    existing = _column_names(client, schema)
    for name, column_type in columns.items():
        if name in existing:
            continue
        for attempt in range(1, 21):
            try:
                client.tables.add_columns(schema, {name: column_type})
                print(f"  + column {schema}.{name}")
                existing.add(name)
                break
            except Exception as e:
                if _is_dup(e):
                    existing.add(name)
                    break
                if not _is_customization_lock(e) or attempt == 20:
                    print(f"  ! column {schema}.{name}  {short_error(e)}")
                    raise
                print(f"  ~ column {schema}.{name} waiting for metadata lock ({attempt}/20)")
                time.sleep(10)
                existing = _column_names(client, schema)
                if name in existing:
                    break


def _ensure_publisher(client) -> str:
    pages = client.records.get(
        "publisher",
        filter=f"uniquename eq '{PUBLISHER_UNIQUE}'",
        select=["publisherid"],
        top=1,
    )
    existing = next((p for page in pages for p in page), None)
    if existing:
        print(f"  = publisher '{PUBLISHER_UNIQUE}' (exists)")
        return existing["publisherid"]
    pid = client.records.create("publisher", {
        "uniquename": PUBLISHER_UNIQUE,
        "friendlyname": "Launch Control",
        "customizationprefix": PUBLISHER_PREFIX,
        "customizationoptionvalueprefix": PUBLISHER_OPTVAL_PREFIX,
        "description": "Publisher for Launch Control",
    })
    print(f"  + publisher '{PUBLISHER_UNIQUE}'")
    return pid


def _ensure_solution(client, publisher_id: str) -> None:
    pages = client.records.get(
        "solution",
        filter=f"uniquename eq '{SOLUTION}'",
        select=["solutionid"],
        top=1,
    )
    if next((s for page in pages for s in page), None):
        print(f"  = solution '{SOLUTION}' (exists)")
        return
    client.records.create("solution", {
        "uniquename": SOLUTION,
        "friendlyname": SOLUTION,
        "version": "1.0.0.0",
        "description": "Unified launch model + staging for shadow trackers",
        "publisherid@odata.bind": f"/publishers({publisher_id})",
    })
    print(f"  + solution '{SOLUTION}'")


def _ensure_table(client, schema: str, cols: dict, primary: str) -> None:
    if client.tables.get(schema):
        print(f"  = table {schema} (exists)")
        _ensure_columns(client, schema, cols)
        return
    for attempt in range(1, 21):
        t0 = time.monotonic()
        try:
            client.tables.create(
                schema,
                cols,
                solution=SOLUTION,
                primary_column=primary,
            )
            print(f"  + table {schema} ({time.monotonic() - t0:.1f}s)")
            _ensure_columns(client, schema, cols)
            return
        except Exception as e:
            if _is_dup(e):
                print(f"  = table {schema} (exists)")
                return
            if not _is_customization_lock(e) or attempt == 20:
                print(f"  ! table {schema}  {short_error(e)}")
                raise
            print(f"  ~ table {schema} waiting for metadata lock ({attempt}/20)")
            time.sleep(10)
            if client.tables.get(schema):
                print(f"  = table {schema} (created while waiting)")
                _ensure_columns(client, schema, cols)
                return


def _ensure_lookup(client, ref: str, name: str, target: str, display: str) -> None:
    cols = client.tables.list_columns(ref) or []
    names = set()
    for c in cols:
        ln = c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None)
        if ln:
            names.add(ln)
    if name in names:
        print(f"  = lookup {ref}.{name} -> {target} (exists)")
        return
    t0 = time.monotonic()
    for attempt in range(1, 21):
        try:
            client.tables.create_lookup_field(
                ref,
                name,
                target,
                display_name=display,
                solution=SOLUTION,
            )
            print(f"  + lookup {ref}.{name} -> {target} ({time.monotonic() - t0:.1f}s)")
            return
        except Exception as e:
            if _is_dup(e):
                print(f"  = lookup {ref}.{name} -> {target} (exists)")
                return
            if not _is_customization_lock(e) or attempt == 20:
                print(f"  ! lookup {ref}.{name} -> {target}  {short_error(e)}")
                raise
            print(f"  ~ lookup {ref}.{name} waiting for metadata lock ({attempt}/20)")
            time.sleep(10)
            cols = client.tables.list_columns(ref) or []
            if any(
                (c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None)) == name
                for c in cols
            ):
                print(f"  = lookup {ref}.{name} -> {target} (created while waiting)")
                return


def _ensure_solution_attribute_components(
    env_url: str,
    tables: list[tuple[str, dict, str]],
    lookups: list[tuple[str, str, str, str]],
) -> None:
    api = env_url.rstrip("/") + "/api/data/v9.2"
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    response = requests.get(
        api + f"/solutions?$select=solutionid&$filter=uniquename eq '{SOLUTION}'",
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    solutions = response.json().get("value", [])
    if len(solutions) != 1:
        raise RuntimeError(f"Expected one unmanaged {SOLUTION} solution.")
    solution_id = solutions[0]["solutionid"]

    response = requests.get(
        api
        + "/solutioncomponents?$select=objectid"
        + f"&$filter=_solutionid_value eq {solution_id} and componenttype eq 2",
        headers=headers,
        timeout=60,
    )
    response.raise_for_status()
    included = {
        row["objectid"].lower() for row in response.json().get("value", [])
    }

    expected_by_table: dict[str, set[str]] = {}
    for table, columns, primary in tables:
        expected_by_table.setdefault(table, set()).update(columns)
        expected_by_table[table].add(primary)
    for table, name, _, _ in lookups:
        expected_by_table.setdefault(table, set()).add(name)

    for table, expected_names in expected_by_table.items():
        response = requests.get(
            api
            + f"/EntityDefinitions(LogicalName='{table}')"
            "?$select=MetadataId,PrimaryIdAttribute",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        entity = response.json()
        expected_names.add(entity["PrimaryIdAttribute"])
        response = requests.get(
            api
            + f"/EntityDefinitions({entity['MetadataId']})/Attributes"
            "?$select=MetadataId,LogicalName",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        attributes = {
            row["LogicalName"]: row["MetadataId"]
            for row in response.json().get("value", [])
        }
        for name in sorted(expected_names):
            attribute_id = attributes.get(name)
            if not attribute_id:
                raise RuntimeError(f"Expected {table}.{name} column is missing.")
            if attribute_id.lower() in included:
                continue
            payload = {
                "ComponentId": attribute_id,
                "ComponentType": 2,
                "SolutionUniqueName": SOLUTION,
                "AddRequiredComponents": True,
                "DoNotIncludeSubcomponents": False,
            }
            for attempt in range(1, 4):
                try:
                    response = requests.post(
                        api + "/AddSolutionComponent",
                        headers=headers,
                        json=payload,
                        timeout=120,
                    )
                    break
                except requests.RequestException:
                    if attempt == 3:
                        raise
                    print(
                        f"  ~ solution field {table}.{name} request timed out "
                        f"({attempt}/3); retrying"
                    )
                    time.sleep(5 * attempt)
            if not response.ok and "already" not in response.text.lower():
                raise RuntimeError(
                    "Adding solution field component failed "
                    f"({response.status_code}): {response.text[:800]}"
                )
            included.add(attribute_id.lower())
            print(f"  + solution field {table}.{name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope",
        choices=("unified", "staging", "all"),
        default="unified",
        help="Which slice of the schema to build (default: unified).",
    )
    parser.add_argument(
        "--with-lookups",
        action="store_true",
        help=(
            "Build the cross-table lookup relationships. Disabled by default "
            "to keep the build fast; tables-only builds skip the lookup phase."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List planned schema changes without changing Dataverse.",
    )
    args = parser.parse_args()

    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    t0 = time.monotonic()
    print(f"== Scope: {args.scope} ==")

    with DataverseClient(env_url, get_credential()) as client:
        common_stg = {
            f"{PREFIX}_sourceid": "string",
            f"{PREFIX}_sourcefile": "string",
            f"{PREFIX}_ingestedat": "datetime",
            f"{PREFIX}_rawjson": "memo",
        }

        staging_tables = [
            (f"{PREFIX}_stg_tracker_a", {
                **common_stg,
                f"{PREFIX}_owneremail": "string",
                f"{PREFIX}_priority": "string",
                f"{PREFIX}_duedate": "datetime",
                f"{PREFIX}_status": "string",
                f"{PREFIX}_notes": "memo",
                f"{PREFIX}_milestonename": "string",
            }, f"{PREFIX}_title"),
            (f"{PREFIX}_stg_tracker_b", {
                **common_stg,
                f"{PREFIX}_owneremail": "string",
                f"{PREFIX}_category": "string",
                f"{PREFIX}_priority": "string",
                f"{PREFIX}_duedate": "datetime",
                f"{PREFIX}_status": "string",
                f"{PREFIX}_milestonename": "string",
            }, f"{PREFIX}_name"),
            (f"{PREFIX}_stg_tracker_c", {
                **common_stg,
                f"{PREFIX}_owneremail": "string",
                f"{PREFIX}_quarter": "string",
                f"{PREFIX}_status": "string",
            }, f"{PREFIX}_initiative"),
            (f"{PREFIX}_stg_tracker_d", {
                **common_stg,
                f"{PREFIX}_owneremail": "string",
                f"{PREFIX}_priority": "string",
                f"{PREFIX}_notes": "memo",
                f"{PREFIX}_milestonename": "string",
            }, f"{PREFIX}_tool"),
            (f"{PREFIX}_stg_tracker_e", {
                **common_stg,
                f"{PREFIX}_owneremail": "string",
                f"{PREFIX}_release": "string",
                f"{PREFIX}_priority": "string",
                f"{PREFIX}_status": "string",
            }, f"{PREFIX}_project"),
        ]

        unified_tables = [
            (f"{PREFIX}_launch", {
                f"{PREFIX}_code": "string",
                f"{PREFIX}_releasewindow": "string",
                f"{PREFIX}_targetdate": "datetime",
                f"{PREFIX}_description": "memo",
                f"{PREFIX}_risksummary": "memo",
                f"{PREFIX}_qualitygatestatus": QualityGateStatus,
                f"{PREFIX}_qualitygatescore": "int",
                f"{PREFIX}_qualitygatefeedback": "memo",
                f"{PREFIX}_qualitygatecheckedon": "datetime",
                f"{PREFIX}_launchstatus": LaunchStatus,
                f"{PREFIX}_priority": Priority,
            }, f"{PREFIX}_name"),
            (f"{PREFIX}_milestone", {
                f"{PREFIX}_quarter": "string",
                f"{PREFIX}_duedate": "datetime",
                f"{PREFIX}_description": "memo",
                f"{PREFIX}_milestonestatus": MilestoneStatus,
            }, f"{PREFIX}_name"),
            (f"{PREFIX}_task", {
                f"{PREFIX}_duedate": "datetime",
                f"{PREFIX}_notes": "memo",
                f"{PREFIX}_isblocked": "bool",
                f"{PREFIX}_blockerreason": "string",
                f"{PREFIX}_taskstatus": TaskStatus,
                f"{PREFIX}_priority": Priority,
                f"{PREFIX}_category": TaskCategory,
                f"{PREFIX}_sourcetracker": SourceTracker,
            }, f"{PREFIX}_title"),
            (f"{PREFIX}_teammember", {
                f"{PREFIX}_email": "string",
                f"{PREFIX}_role": "string",
            }, f"{PREFIX}_name"),
            (f"{PREFIX}_statusupdate", {
                f"{PREFIX}_summary": "memo",
                f"{PREFIX}_postedat": "datetime",
                f"{PREFIX}_health": Health,
            }, f"{PREFIX}_title"),
        ]

        tables_to_build = []
        if args.scope in ("unified", "all"):
            tables_to_build += unified_tables
        if args.scope in ("staging", "all"):
            tables_to_build += staging_tables

        unified_lookups = [
            (f"{PREFIX}_launch",       f"{PREFIX}_ownerid",       f"{PREFIX}_teammember", "Owner"),
            (f"{PREFIX}_milestone",    f"{PREFIX}_launchid",      f"{PREFIX}_launch",     "Launch"),
            (f"{PREFIX}_milestone",    f"{PREFIX}_ownerid",       f"{PREFIX}_teammember", "Owner"),
            (f"{PREFIX}_task",         f"{PREFIX}_milestoneid",   f"{PREFIX}_milestone",  "Milestone"),
            (f"{PREFIX}_task",         f"{PREFIX}_launchid",      f"{PREFIX}_launch",     "Launch"),
            (f"{PREFIX}_task",         f"{PREFIX}_assignedtoid",  f"{PREFIX}_teammember", "Assigned To"),
            (f"{PREFIX}_statusupdate", f"{PREFIX}_launchid",      f"{PREFIX}_launch",     "Launch"),
            (f"{PREFIX}_statusupdate", f"{PREFIX}_milestoneid",   f"{PREFIX}_milestone",  "Milestone"),
            (f"{PREFIX}_statusupdate", f"{PREFIX}_taskid",        f"{PREFIX}_task",       "Task"),
            (f"{PREFIX}_statusupdate", f"{PREFIX}_authorid",      f"{PREFIX}_teammember", "Author"),
        ]
        provenance_lookups = [
            (f"{PREFIX}_launch",    f"{PREFIX}_sourcestagingeid", f"{PREFIX}_stg_tracker_e", "Source (Tracker E)"),
            (f"{PREFIX}_milestone", f"{PREFIX}_sourcestagingcid", f"{PREFIX}_stg_tracker_c", "Source (Tracker C)"),
            (f"{PREFIX}_task",      f"{PREFIX}_sourcestagingaid", f"{PREFIX}_stg_tracker_a", "Source (Tracker A)"),
            (f"{PREFIX}_task",      f"{PREFIX}_sourcestagingbid", f"{PREFIX}_stg_tracker_b", "Source (Tracker B)"),
            (f"{PREFIX}_task",      f"{PREFIX}_sourcestagingdid", f"{PREFIX}_stg_tracker_d", "Source (Tracker D)"),
        ]

        lookups_to_build = []
        if args.with_lookups:
            if args.scope in ("unified", "all"):
                lookups_to_build += unified_lookups
            if args.scope in ("staging", "all"):
                lookups_to_build += provenance_lookups

        if args.dry_run:
            print("\n== Dry run: no Dataverse changes will be made ==")
            print(f"Publisher: {PUBLISHER_UNIQUE}")
            print(f"Solution: {SOLUTION}")
            print("Tables:")
            for schema, columns, primary in tables_to_build:
                print(f"  {schema} ({len(columns) + 2} fields including primary columns)")
            print("Lookups:")
            if lookups_to_build:
                for ref, name, target, display in lookups_to_build:
                    print(f"  {ref}.{name} -> {target} ({display})")
            else:
                print("  none (pass --with-lookups to include relationships)")
            return

        print("== Publisher + Solution ==")
        publisher_id = _ensure_publisher(client)
        _ensure_solution(client, publisher_id)

        print(f"\n== Tables (serial; metadata lock is per-env) [{len(tables_to_build)}] ==")
        for schema, cols, primary in tables_to_build:
            _ensure_table(client, schema, cols, primary)

        if not args.with_lookups:
            print("\n== Lookups (skipped; pass --with-lookups to enable) ==")
        else:
            print(f"\n== Lookups (serial) [{len(lookups_to_build)}] ==")
            for ref, name, target, display in lookups_to_build:
                _ensure_lookup(client, ref, name, target, display)

        print("\n== Solution field components ==")
        _ensure_solution_attribute_components(
            env_url,
            tables_to_build,
            lookups_to_build,
        )

        print(f"\n=== Done in {time.monotonic() - t0:.1f}s ===")


if __name__ == "__main__":
    main()
