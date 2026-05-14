"""Session-generated LaunchControl builder (per lc-datamodel skill).

Builds publisher + solution + unified (5) + staging (5) tables + all 15
lookups. Strictly serial. Idempotent. Bounded retries on transient lock /
timeout errors.
"""
import os
import sys
import time
from enum import Enum

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

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


class SourceTracker(Enum):
    TrackerA = 10600701
    TrackerB = 10600702
    TrackerD = 10600703


TRANSIENT_HINTS = (
    "customizationlock",
    "timeout",
    "timed out",
    "throttle",
    "429",
    "503",
    "service unavailable",
    "operation could not be completed",
)


def _is_dup(e):
    m = str(e).lower()
    return any(s in m for s in ("already exists", "duplicate", "is not unique"))


def _is_transient(e):
    m = str(e).lower()
    return any(s in m for s in TRANSIENT_HINTS)


def _retry(fn, *, label):
    delay = 2.0
    for attempt in range(1, 9):
        try:
            return fn()
        except Exception as e:
            if _is_dup(e):
                raise
            if not _is_transient(e) or attempt == 8:
                raise
            print(f"  ~ {label}: transient (attempt {attempt}): {str(e)[:120]}; retry in {delay:.0f}s")
            time.sleep(delay)
            delay = min(delay * 1.6, 30.0)


def ensure_publisher(client):
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


def ensure_solution(client, publisher_id):
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


def ensure_table(client, schema, cols, primary):
    if client.tables.get(schema):
        print(f"  = table {schema} (exists)")
        return
    t0 = time.monotonic()
    def _do():
        client.tables.create(schema, cols, solution=SOLUTION, primary_column=primary)
    try:
        _retry(_do, label=f"table {schema}")
        print(f"  + table {schema} ({time.monotonic() - t0:.1f}s)")
    except Exception as e:
        if _is_dup(e):
            print(f"  = table {schema} (exists)")
        else:
            raise


def ensure_lookup(client, ref, name, target, display):
    try:
        cols = client.tables.list_columns(ref) or []
        names = set()
        for c in cols:
            ln = c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None)
            if ln:
                names.add(ln)
        if name in names:
            print(f"  = lookup {ref}.{name} -> {target} (exists)")
            return
    except Exception:
        pass
    t0 = time.monotonic()
    def _do():
        client.tables.create_lookup_field(ref, name, target, display_name=display, solution=SOLUTION)
    try:
        _retry(_do, label=f"lookup {ref}.{name}")
        print(f"  + lookup {ref}.{name} -> {target} ({time.monotonic() - t0:.1f}s)")
    except Exception as e:
        if _is_dup(e):
            print(f"  = lookup {ref}.{name} -> {target} (exists)")
        else:
            raise


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    t_start = time.monotonic()

    common_stg = {
        f"{PREFIX}_sourceid": "string",
        f"{PREFIX}_sourcefile": "string",
        f"{PREFIX}_ingestedat": "datetime",
        f"{PREFIX}_rawjson": "memo",
    }

    # Leaf tables first (no outbound lookups): teammember + all staging.
    leaf_tables = [
        (f"{PREFIX}_teammember", {
            f"{PREFIX}_email": "string",
            f"{PREFIX}_role": "string",
        }, f"{PREFIX}_name"),
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

    # Referencing tables next.
    ref_tables = [
        (f"{PREFIX}_launch", {
            f"{PREFIX}_code": "string",
            f"{PREFIX}_releasewindow": "string",
            f"{PREFIX}_targetdate": "datetime",
            f"{PREFIX}_description": "memo",
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
            f"{PREFIX}_taskstatus": TaskStatus,
            f"{PREFIX}_priority": Priority,
            f"{PREFIX}_category": TaskCategory,
            f"{PREFIX}_sourcetracker": SourceTracker,
        }, f"{PREFIX}_title"),
        (f"{PREFIX}_statusupdate", {
            f"{PREFIX}_summary": "memo",
            f"{PREFIX}_postedat": "datetime",
            f"{PREFIX}_health": Health,
        }, f"{PREFIX}_title"),
    ]

    lookups = [
        # Unified cross-table (10)
        (f"{PREFIX}_launch",       f"{PREFIX}_ownerid",          f"{PREFIX}_teammember",   "Owner"),
        (f"{PREFIX}_milestone",    f"{PREFIX}_launchid",         f"{PREFIX}_launch",       "Launch"),
        (f"{PREFIX}_milestone",    f"{PREFIX}_ownerid",          f"{PREFIX}_teammember",   "Owner"),
        (f"{PREFIX}_task",         f"{PREFIX}_milestoneid",      f"{PREFIX}_milestone",    "Milestone"),
        (f"{PREFIX}_task",         f"{PREFIX}_launchid",         f"{PREFIX}_launch",       "Launch"),
        (f"{PREFIX}_task",         f"{PREFIX}_assignedtoid",     f"{PREFIX}_teammember",   "Assigned To"),
        (f"{PREFIX}_statusupdate", f"{PREFIX}_launchid",         f"{PREFIX}_launch",       "Launch"),
        (f"{PREFIX}_statusupdate", f"{PREFIX}_milestoneid",      f"{PREFIX}_milestone",    "Milestone"),
        (f"{PREFIX}_statusupdate", f"{PREFIX}_taskid",           f"{PREFIX}_task",         "Task"),
        (f"{PREFIX}_statusupdate", f"{PREFIX}_authorid",         f"{PREFIX}_teammember",   "Author"),
        # Provenance unified -> staging (5)
        (f"{PREFIX}_launch",       f"{PREFIX}_sourcestagingeid", f"{PREFIX}_stg_tracker_e", "Source (Tracker E)"),
        (f"{PREFIX}_milestone",    f"{PREFIX}_sourcestagingcid", f"{PREFIX}_stg_tracker_c", "Source (Tracker C)"),
        (f"{PREFIX}_task",         f"{PREFIX}_sourcestagingaid", f"{PREFIX}_stg_tracker_a", "Source (Tracker A)"),
        (f"{PREFIX}_task",         f"{PREFIX}_sourcestagingbid", f"{PREFIX}_stg_tracker_b", "Source (Tracker B)"),
        (f"{PREFIX}_task",         f"{PREFIX}_sourcestagingdid", f"{PREFIX}_stg_tracker_d", "Source (Tracker D)"),
    ]

    with DataverseClient(env_url, get_credential()) as client:
        print("== Publisher + Solution ==")
        publisher_id = ensure_publisher(client)
        ensure_solution(client, publisher_id)

        print(f"\n== Leaf tables [{len(leaf_tables)}] ==")
        for schema, cols, primary in leaf_tables:
            ensure_table(client, schema, cols, primary)

        print(f"\n== Referencing tables [{len(ref_tables)}] ==")
        for schema, cols, primary in ref_tables:
            ensure_table(client, schema, cols, primary)

        print(f"\n== Lookups [{len(lookups)}] ==")
        for ref, name, target, display in lookups:
            ensure_lookup(client, ref, name, target, display)

    print(f"\n== Done in {time.monotonic() - t_start:.1f}s ==")


if __name__ == "__main__":
    main()
