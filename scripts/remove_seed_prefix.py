"""Strip the [SEED] title prefix from Ep-7 baseline tasks.

Pair script to scripts/seed_q3_sample_tasks.py. The seeder uses a
"[SEED] " title prefix as its idempotency marker (lc_task has no
lc_source column). Once the demo data is in place and you no longer
need to re-seed in place, run this once to clean the titles up before
sharing the environment.

Behavior:
- Finds every open lc_task on Q3 Widget Launch whose lc_title starts
  with "[SEED] " and PATCHes lc_title to the un-prefixed value.
- Idempotent. Re-running is a no-op once the prefix is gone.
- Dry-run mode prints what would change without writing.

Run:

    python scripts/remove_seed_prefix.py              # dry-run
    python scripts/remove_seed_prefix.py --commit     # writes
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import get_token, load_env  # noqa: E402


LAUNCH_NAME = "Q3 Widget Launch"
TITLE_PREFIX = "[SEED] "


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def resolve_launch_id(env_url: str, token: str) -> str:
    safe = LAUNCH_NAME.replace("'", "''")
    r = requests.get(
        f"{env_url}/api/data/v9.2/lc_launchs",
        params={
            "$select": "lc_launchid",
            "$filter": f"lc_name eq '{safe}' and statecode eq 0",
        },
        headers=_headers(token),
        timeout=60,
    )
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        raise RuntimeError(f"No launch named '{LAUNCH_NAME}' found.")
    return rows[0]["lc_launchid"]


def list_seed_tasks(env_url: str, token: str, launch_id: str) -> list[dict]:
    r = requests.get(
        f"{env_url}/api/data/v9.2/lc_tasks",
        params={
            "$select": "lc_taskid,lc_title",
            "$filter": (
                f"_lc_launchid_value eq {launch_id} and "
                f"startswith(lc_title,'{TITLE_PREFIX.strip()}')"
            ),
        },
        headers=_headers(token),
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("value", [])


def strip_prefix(env_url: str, token: str, task: dict) -> None:
    new_title = task["lc_title"][len(TITLE_PREFIX):] if task["lc_title"].startswith(TITLE_PREFIX) else task["lc_title"]
    r = requests.patch(
        f"{env_url}/api/data/v9.2/lc_tasks({task['lc_taskid']})",
        headers=_headers(token),
        json={"lc_title": new_title},
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"patch {task['lc_taskid']} failed: {r.status_code} {r.text[:400]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="Write changes. Without this flag, runs as dry-run.")
    args = ap.parse_args()

    load_env()
    env_url = os.environ.get("DATAVERSE_URL")
    if not env_url:
        print("DATAVERSE_URL not set in .env", file=sys.stderr)
        return 1
    env_url = env_url.rstrip("/")

    token = get_token()
    launch_id = resolve_launch_id(env_url, token)
    tasks = list_seed_tasks(env_url, token, launch_id)
    print(f"Found {len(tasks)} [SEED] task(s) on '{LAUNCH_NAME}'.")

    if not tasks:
        print("Nothing to do.")
        return 0

    for t in tasks:
        new_title = t["lc_title"][len(TITLE_PREFIX):]
        print(f"  {t['lc_taskid']}  '{t['lc_title']}' -> '{new_title}'")

    if not args.commit:
        print("")
        print("Dry-run. Re-run with --commit to apply.")
        return 0

    for t in tasks:
        strip_prefix(env_url, token, t)
    print(f"Stripped prefix from {len(tasks)} task(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
