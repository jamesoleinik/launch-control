"""Episode 1 teardown: drop the 12 lc_ tables and the LaunchControl solution.

Run this BEFORE re-recording the Episode 1 walkthrough so the env looks fresh.
Idempotent: tables/solution that don't exist are skipped quietly.

  python scripts/teardown_ep1.py

Order of operations:
  1. DELETE EntityDefinitions(LogicalName='lc_xxx') for each lc_ table, in
     reverse dependency order (children before parents). Deleting an entity
     in Dataverse also removes its rows, columns, relationships, and any
     forms/views, so we do not need to clean those up separately.
  2. DELETE solutions(<id>) for 'LaunchControl' so the next create_datamodel.py
     run shows "Solution created" rather than "already exists".
  3. Publisher 'launchcontrol' is intentionally kept -- the customization
     prefix 'lc' is permanent on any prior components and reusing it is fine.

Reads .env via scripts.auth.
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env  # noqa: E402
from scripts._resilient import short_error  # noqa: E402

# Deletion is partitioned into waves. Within a wave, tables can be dropped
# in parallel because they share no remaining references. Each wave waits
# for all jobs in the prior wave to complete before starting.
#
# Wave 1: child tables that hold lookups to other lc_ tables. Once these are
#         gone, the remaining tables are leaves (no incoming lc_ references).
# Wave 2: lc_launch -- target of milestone/teammember/statusupdate, which
#         are dropped in wave 1.
# Wave 3: lc_importrun -- target of EVERY other table's ImportRunId lookup.
WAVES = [
    [
        "lc_task",          # lookups -> milestone, teammember
        "lc_statusupdate",  # lookup -> launch
        "lc_milestone",     # lookup -> launch
        "lc_teammember",    # lookup -> launch
        "lc_trackera",      # lookup -> importrun only
        "lc_trackerb",
        "lc_trackerc",
        "lc_trackerd",
        "lc_trackere",
        "lc_sourcefile",    # lookup -> importrun
    ],
    ["lc_launch"],
    ["lc_importrun"],
]

# Backward-compat: flat list still useful for tests / external callers.
TABLES = [t for wave in WAVES for t in wave]

SOLUTION_UNIQUE_NAME = "LaunchControl"


def _drop_table(url: str, headers: dict, logical: str, max_attempts: int = 5) -> str:
    """DELETE one EntityDefinition with retry on transient/dependency errors."""
    endpoint = f"{url}/api/data/v9.2/EntityDefinitions(LogicalName='{logical}')"
    for n in range(1, max_attempts + 1):
        try:
            r = requests.delete(endpoint, headers=headers, timeout=600)
        except requests.RequestException as e:
            if n < max_attempts:
                delay = 2.0 * (2 ** (n - 1))
                print(f"  {logical}: network error (attempt {n}); retrying in {delay:.0f}s -- {short_error(e)}")
                time.sleep(delay)
                continue
            print(f"  ERROR {logical}: {short_error(e)}")
            return "failed"

        if r.status_code in (204, 200):
            print(f"  Dropped: {logical}")
            return "dropped"
        if r.status_code == 404:
            print(f"  {logical} doesn't exist, skipping.")
            return "missing"

        body = r.text or ""
        body_lower = body.lower()
        # Retry on dependency/lock/transient errors.
        retryable = (
            "dependency" in body_lower
            or "is referenced" in body_lower
            or "in use" in body_lower
            or "cannot start another" in body_lower
            or "entitycustomization" in body_lower
            or "severe error" in body_lower
            or r.status_code in (429, 500, 502, 503, 504)
        )
        if retryable and n < max_attempts:
            delay = 2.0 * (2 ** (n - 1))
            preview = body[:160].replace("\n", " ").strip()
            print(f"  {logical}: HTTP {r.status_code} (attempt {n}); retrying in {delay:.0f}s -- {preview}")
            time.sleep(delay)
            continue

        preview = body[:240].replace("\n", " ").strip()
        print(f"  ERROR {logical}: HTTP {r.status_code} -- {preview}")
        return "failed"
    return "failed"


def _drop_solution(url: str, headers: dict, unique_name: str) -> str:
    r = requests.get(
        f"{url}/api/data/v9.2/solutions"
        f"?$filter=uniquename eq '{unique_name}'&$select=solutionid",
        headers=headers, timeout=30,
    )
    if not r.ok:
        print(f"  ERROR querying solution {unique_name}: HTTP {r.status_code}")
        return "failed"
    items = r.json().get("value", [])
    if not items:
        print(f"  Solution {unique_name} doesn't exist, skipping.")
        return "missing"
    sid = items[0]["solutionid"]
    r = requests.delete(
        f"{url}/api/data/v9.2/solutions({sid})",
        headers=headers, timeout=120,
    )
    if r.status_code in (204, 200):
        print(f"  Dropped solution: {unique_name}")
        return "dropped"
    preview = (r.text or "")[:240].replace("\n", " ").strip()
    print(f"  ERROR dropping solution {unique_name}: HTTP {r.status_code} -- {preview}")
    return "failed"


def main() -> int:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-Version": "4.0",
        "Content-Type": "application/json",
    }

    print(f"\nTeardown target: {url}")
    total_tables = sum(len(w) for w in WAVES)
    print(f"Dropping {total_tables} lc_ tables in {len(WAVES)} wave(s) + solution '{SOLUTION_UNIQUE_NAME}'\n")

    failures = 0
    for i, wave in enumerate(WAVES, 1):
        print(f"--- Wave {i} ({len(wave)} table{'s' if len(wave) != 1 else ''} in parallel) ---")
        workers = min(len(wave), 8)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_table = {
                pool.submit(_drop_table, url, headers, t): t for t in wave
            }
            for fut in as_completed(future_to_table):
                if fut.result() == "failed":
                    failures += 1
        print()

    print("--- Solution ---")
    if _drop_solution(url, headers, SOLUTION_UNIQUE_NAME) == "failed":
        failures += 1

    print(f"\nTeardown complete. Failures: {failures}")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
