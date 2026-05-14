"""Build LaunchControl schema, optimized for wall-clock.

Background
----------
The serial build (build_launchcontrol_schema.py) takes ~12 minutes because each
table create blocks ~28s and each lookup create blocks ~23s waiting for
Dataverse's metadata propagation. Total: 10 tables + 15 lookups = ~12 min.

Strategy
--------
1. Publisher + solution: serial, fast (existing records reused).
2. Tables: split into two phases by dependency.
   - Leaf phase: lc_teammember + 5 lc_stg_tracker_* tables (no outbound lookups).
   - Referencing phase: lc_launch, lc_milestone, lc_task, lc_statusupdate.
   Within each phase, fire all creates concurrently against a small thread pool
   with retry-on-CustomizationLockException backoff. If Dataverse serializes
   them at the server, total wall-clock = sum(per-op latency) -- same as today.
   If parallelism is honored even partially, total wall-clock approaches
   max(per-op latency) per phase.
3. Lookups: 15 independent POST /RelationshipDefinitions calls. Fired in
   parallel with the same retry-on-lock pattern. Microsoft docs are ambiguous
   on whether the lock is per-environment or per-entity-pair; if per-pair,
   ~15x speedup; if per-env, we degrade to current speed.

Fallback
--------
- Every operation has bounded retry (up to 5 attempts, exponential backoff
  capped at 30s). On final failure we surface the error.
- Pre-existence checks skip already-created items, so a re-run is a no-op
  (useful for partial-failure recovery).

The original build_launchcontrol_schema.py is preserved unchanged as a
known-good serial baseline.

Scope:
  --scope unified  (default) -- 5 unified tables + 10 cross-table lookups.
  --scope staging            -- 5 staging tables + 5 provenance lookups.
  --scope all                -- everything (~3 phases run end-to-end).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Callable, Iterable, List, Optional, Tuple, TypeVar

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_credential, load_env
from scripts._resilient import short_error
from PowerPlatform.Dataverse.client import DataverseClient

# ---------------------------------------------------------------------------
# Schema definition (kept in sync with build_launchcontrol_schema.py)
# ---------------------------------------------------------------------------

PREFIX = "lc"
SOLUTION = "LaunchControl"
PUBLISHER_UNIQUE = "LaunchControl"
PUBLISHER_PREFIX = "lc"
PUBLISHER_OPTVAL_PREFIX = 10600

# Parallelism knobs. Tuned conservatively to avoid hammering Dataverse if the
# per-env lock is real -- a 4-wide pool gives us roughly 4x best-case speedup
# but only ~4 concurrent retry storms on the worst case.
TABLE_POOL_WIDTH = 1
# Lookups run serially. Empirically the env-wide EntityCustomization lock
# serializes lookup creates at the server anyway, so any pool width > 1 just
# wastes wall-clock time on CustomizationLockException retry storms. Serial
# lookups finish in ~23s each with zero retries -- faster than parallel +
# retry-burn.
LOOKUP_POOL_WIDTH = 1

# Retry policy for CustomizationLockException and other transient errors.
MAX_ATTEMPTS = 8
INITIAL_BACKOFF_S = 2.0
MAX_BACKOFF_S = 30.0


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


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

T = TypeVar("T")

_TRANSIENT_PHRASES = (
    "customizationlockexception",
    "another customization operation is running",
    "0x80072321",
    "0x80040216",
    "metadata cache",
    "timed out",
    "timeout",
    "service unavailable",
    "throttle",
    "transient",
)


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(p in msg for p in _TRANSIENT_PHRASES)


def _is_duplicate(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(p in msg for p in ("already exists", "duplicate", "is not unique"))


def with_retry(label: str, fn: Callable[[], T]) -> T:
    """Run fn() with exponential backoff for transient metadata errors."""
    backoff = INITIAL_BACKOFF_S
    last_exc: Optional[BaseException] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_duplicate(exc):
                raise
            if not _is_transient(exc) or attempt == MAX_ATTEMPTS:
                raise
            sleep_for = min(backoff, MAX_BACKOFF_S)
            print(
                f"  ~ {label} transient on attempt {attempt}: "
                f"{short_error(exc)} -- retrying in {sleep_for:.1f}s"
            )
            time.sleep(sleep_for)
            backoff *= 2
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Thread-local client
# ---------------------------------------------------------------------------

_tls = threading.local()


def _get_client(env_url: str) -> DataverseClient:
    """Each worker thread holds its own DataverseClient to avoid contention on
    shared HTTP/auth state inside the SDK. Credentials are reused (the cred
    object IS thread-safe for token acquisition)."""
    client = getattr(_tls, "client", None)
    if client is None:
        client = DataverseClient(env_url, get_credential())
        _tls.client = client
    return client


# ---------------------------------------------------------------------------
# Publisher / solution (serial; trivial)
# ---------------------------------------------------------------------------


def ensure_publisher(client: DataverseClient) -> str:
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
    pid = client.records.create(
        "publisher",
        {
            "uniquename": PUBLISHER_UNIQUE,
            "friendlyname": "Launch Control",
            "customizationprefix": PUBLISHER_PREFIX,
            "customizationoptionvalueprefix": PUBLISHER_OPTVAL_PREFIX,
            "description": "Publisher for Launch Control",
        },
    )
    print(f"  + publisher '{PUBLISHER_UNIQUE}'")
    return pid


def ensure_solution(client: DataverseClient, publisher_id: str) -> None:
    pages = client.records.get(
        "solution",
        filter=f"uniquename eq '{SOLUTION}'",
        select=["solutionid"],
        top=1,
    )
    if next((s for page in pages for s in page), None):
        print(f"  = solution '{SOLUTION}' (exists)")
        return
    client.records.create(
        "solution",
        {
            "uniquename": SOLUTION,
            "friendlyname": SOLUTION,
            "version": "1.0.0.0",
            "description": "Unified launch model + staging for shadow trackers",
            "publisherid@odata.bind": f"/publishers({publisher_id})",
        },
    )
    print(f"  + solution '{SOLUTION}'")


# ---------------------------------------------------------------------------
# Parallel table / lookup creation
# ---------------------------------------------------------------------------


def create_table(env_url: str, schema: str, cols: dict, primary: str) -> str:
    client = _get_client(env_url)
    if client.tables.get(schema):
        return f"  = table {schema} (exists)"
    t0 = time.monotonic()
    try:
        with_retry(
            f"table {schema}",
            lambda: client.tables.create(
                schema, cols, solution=SOLUTION, primary_column=primary
            ),
        )
        return f"  + table {schema} ({time.monotonic() - t0:.1f}s)"
    except Exception as exc:  # noqa: BLE001
        if _is_duplicate(exc):
            return f"  = table {schema} (exists, race)"
        raise


def create_lookup(
    env_url: str, ref: str, name: str, target: str, display: str
) -> str:
    client = _get_client(env_url)
    try:
        cols = client.tables.list_columns(ref) or []
        names = set()
        for c in cols:
            ln = c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None)
            if ln:
                names.add(ln)
        if name in names:
            return f"  = lookup {ref}.{name} -> {target} (exists)"
    except Exception:  # noqa: BLE001
        pass
    t0 = time.monotonic()
    try:
        with_retry(
            f"lookup {ref}.{name}",
            lambda: client.tables.create_lookup_field(
                ref, name, target, display_name=display, solution=SOLUTION
            ),
        )
        return f"  + lookup {ref}.{name} -> {target} ({time.monotonic() - t0:.1f}s)"
    except Exception as exc:  # noqa: BLE001
        if _is_duplicate(exc):
            return f"  = lookup {ref}.{name} -> {target} (exists, race)"
        raise


def run_pool(label: str, jobs: Iterable[Tuple[Callable, tuple]], width: int) -> None:
    jobs = list(jobs)
    print(f"\n== {label} ({len(jobs)} ops, pool width {width}) ==")
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=width) as ex:
        futures = {ex.submit(fn, *args): (fn, args) for fn, args in jobs}
        for fut in as_completed(futures):
            try:
                line = fut.result()
                print(line)
            except Exception as exc:  # noqa: BLE001
                fn, args = futures[fut]
                print(f"  ! {fn.__name__}{args[1:3]} {short_error(exc)}")
                raise
    print(f"  -- {label} wall-clock: {time.monotonic() - t0:.1f}s")


# ---------------------------------------------------------------------------
# Schema lists
# ---------------------------------------------------------------------------

COMMON_STG = {
    f"{PREFIX}_sourceid": "string",
    f"{PREFIX}_sourcefile": "string",
    f"{PREFIX}_ingestedat": "datetime",
    f"{PREFIX}_rawjson": "memo",
}

LEAF_TABLES = [
    (
        f"{PREFIX}_teammember",
        {f"{PREFIX}_email": "string", f"{PREFIX}_role": "string"},
        f"{PREFIX}_name",
    ),
    (
        f"{PREFIX}_stg_tracker_a",
        {
            **COMMON_STG,
            f"{PREFIX}_owneremail": "string",
            f"{PREFIX}_priority": "string",
            f"{PREFIX}_duedate": "datetime",
            f"{PREFIX}_status": "string",
            f"{PREFIX}_notes": "memo",
            f"{PREFIX}_milestonename": "string",
        },
        f"{PREFIX}_title",
    ),
    (
        f"{PREFIX}_stg_tracker_b",
        {
            **COMMON_STG,
            f"{PREFIX}_owneremail": "string",
            f"{PREFIX}_category": "string",
            f"{PREFIX}_priority": "string",
            f"{PREFIX}_duedate": "datetime",
            f"{PREFIX}_status": "string",
            f"{PREFIX}_milestonename": "string",
        },
        f"{PREFIX}_name",
    ),
    (
        f"{PREFIX}_stg_tracker_c",
        {
            **COMMON_STG,
            f"{PREFIX}_owneremail": "string",
            f"{PREFIX}_quarter": "string",
            f"{PREFIX}_status": "string",
        },
        f"{PREFIX}_initiative",
    ),
    (
        f"{PREFIX}_stg_tracker_d",
        {
            **COMMON_STG,
            f"{PREFIX}_owneremail": "string",
            f"{PREFIX}_priority": "string",
            f"{PREFIX}_notes": "memo",
            f"{PREFIX}_milestonename": "string",
        },
        f"{PREFIX}_tool",
    ),
    (
        f"{PREFIX}_stg_tracker_e",
        {
            **COMMON_STG,
            f"{PREFIX}_owneremail": "string",
            f"{PREFIX}_release": "string",
            f"{PREFIX}_priority": "string",
            f"{PREFIX}_status": "string",
        },
        f"{PREFIX}_project",
    ),
]

REFERENCING_TABLES = [
    (
        f"{PREFIX}_launch",
        {
            f"{PREFIX}_code": "string",
            f"{PREFIX}_releasewindow": "string",
            f"{PREFIX}_targetdate": "datetime",
            f"{PREFIX}_description": "memo",
            f"{PREFIX}_launchstatus": LaunchStatus,
            f"{PREFIX}_priority": Priority,
        },
        f"{PREFIX}_name",
    ),
    (
        f"{PREFIX}_milestone",
        {
            f"{PREFIX}_quarter": "string",
            f"{PREFIX}_duedate": "datetime",
            f"{PREFIX}_description": "memo",
            f"{PREFIX}_milestonestatus": MilestoneStatus,
        },
        f"{PREFIX}_name",
    ),
    (
        f"{PREFIX}_task",
        {
            f"{PREFIX}_duedate": "datetime",
            f"{PREFIX}_notes": "memo",
            f"{PREFIX}_taskstatus": TaskStatus,
            f"{PREFIX}_priority": Priority,
            f"{PREFIX}_category": TaskCategory,
            f"{PREFIX}_sourcetracker": SourceTracker,
        },
        f"{PREFIX}_title",
    ),
    (
        f"{PREFIX}_statusupdate",
        {
            f"{PREFIX}_summary": "memo",
            f"{PREFIX}_postedat": "datetime",
            f"{PREFIX}_health": Health,
        },
        f"{PREFIX}_title",
    ),
]

UNIFIED_LOOKUPS: List[Tuple[str, str, str, str]] = [
    (f"{PREFIX}_launch",       f"{PREFIX}_ownerid",      f"{PREFIX}_teammember", "Owner"),
    (f"{PREFIX}_milestone",    f"{PREFIX}_launchid",     f"{PREFIX}_launch",     "Launch"),
    (f"{PREFIX}_milestone",    f"{PREFIX}_ownerid",      f"{PREFIX}_teammember", "Owner"),
    (f"{PREFIX}_task",         f"{PREFIX}_milestoneid",  f"{PREFIX}_milestone",  "Milestone"),
    (f"{PREFIX}_task",         f"{PREFIX}_launchid",     f"{PREFIX}_launch",     "Launch"),
    (f"{PREFIX}_task",         f"{PREFIX}_assignedtoid", f"{PREFIX}_teammember", "Assigned To"),
    (f"{PREFIX}_statusupdate", f"{PREFIX}_launchid",     f"{PREFIX}_launch",     "Launch"),
    (f"{PREFIX}_statusupdate", f"{PREFIX}_milestoneid",  f"{PREFIX}_milestone",  "Milestone"),
    (f"{PREFIX}_statusupdate", f"{PREFIX}_taskid",       f"{PREFIX}_task",       "Task"),
    (f"{PREFIX}_statusupdate", f"{PREFIX}_authorid",     f"{PREFIX}_teammember", "Author"),
]

PROVENANCE_LOOKUPS: List[Tuple[str, str, str, str]] = [
    (f"{PREFIX}_launch",    f"{PREFIX}_sourcestagingeid", f"{PREFIX}_stg_tracker_e", "Source (Tracker E)"),
    (f"{PREFIX}_milestone", f"{PREFIX}_sourcestagingcid", f"{PREFIX}_stg_tracker_c", "Source (Tracker C)"),
    (f"{PREFIX}_task",      f"{PREFIX}_sourcestagingaid", f"{PREFIX}_stg_tracker_a", "Source (Tracker A)"),
    (f"{PREFIX}_task",      f"{PREFIX}_sourcestagingbid", f"{PREFIX}_stg_tracker_b", "Source (Tracker B)"),
    (f"{PREFIX}_task",      f"{PREFIX}_sourcestagingdid", f"{PREFIX}_stg_tracker_d", "Source (Tracker D)"),
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
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
            "because the per-env EntityCustomization lock causes lookup "
            "creation to thrash with CustomizationLockException retries. "
            "Re-enable once a serial lookup pass is added."
        ),
    )
    args = parser.parse_args()

    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    t0 = time.monotonic()
    print(f"== Scope: {args.scope} ==")

    with DataverseClient(env_url, get_credential()) as client:
        print("== Publisher + Solution ==")
        publisher_id = ensure_publisher(client)
        ensure_solution(client, publisher_id)

    # Phase A: leaf tables -- no outbound lookups, fully independent.
    # In unified scope, this is just lc_teammember. In staging scope, the 5
    # stg tables. In all scope, both.
    leaf_tables = []
    if args.scope in ("unified", "all"):
        leaf_tables += [t for t in LEAF_TABLES if t[0] == f"{PREFIX}_teammember"]
    if args.scope in ("staging", "all"):
        leaf_tables += [t for t in LEAF_TABLES if t[0] != f"{PREFIX}_teammember"]
    if leaf_tables:
        leaf_jobs = [
            (create_table, (env_url, schema, cols, primary))
            for schema, cols, primary in leaf_tables
        ]
        run_pool("Phase A: leaf tables", leaf_jobs, TABLE_POOL_WIDTH)

    # Phase B: referencing tables -- only present in the unified scope.
    if args.scope in ("unified", "all"):
        ref_jobs = [
            (create_table, (env_url, schema, cols, primary))
            for schema, cols, primary in REFERENCING_TABLES
        ]
        run_pool("Phase B: referencing tables", ref_jobs, TABLE_POOL_WIDTH)

    # Phase C: lookups. Skipped by default -- see --with-lookups.
    lookups = []
    if args.with_lookups:
        if args.scope in ("unified", "all"):
            lookups += UNIFIED_LOOKUPS
        if args.scope in ("staging", "all"):
            lookups += PROVENANCE_LOOKUPS
    else:
        print("\n== Phase C: lookups (skipped; pass --with-lookups to enable) ==")
    if lookups:
        lookup_jobs = [
            (create_lookup, (env_url, ref, name, target, display))
            for ref, name, target, display in lookups
        ]
        run_pool("Phase C: lookups", lookup_jobs, LOOKUP_POOL_WIDTH)

    print(f"\n=== Done in {time.monotonic() - t0:.1f}s ===")


if __name__ == "__main__":
    main()
