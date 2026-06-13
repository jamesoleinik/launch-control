"""Seed Q3 Widget Launch with sample lc_task rows for the Ep-7 demo.

Why: Episode 7's Part 2 (the on-camera "run the sweep" beat) needs an
existing baseline of tasks on Q3 Widget Launch so the skill's dedup
step (which uses the new MCP `search` tool over rows AND attached files)
is the visible value beat. Two seeded tasks are deliberate dedup
targets for the on-camera findings: the export-crash bug matches
`sample-feedback.pdf`, and the pricing-mismatch bug matches the seed
email. On-camera, those new findings should NOT create new tasks. They
should attach to the existing matching task and update its description.

What this script does:

1. Resolves the Q3 Widget Launch row via the Dataverse Web API.
2. Deletes any prior tasks on that launch whose title starts with
   "[SEED]" so the script is idempotent.
3. Creates 10 sample `lc_task` rows on that launch via POST to
   `/api/data/v9.2/lc_tasks`. Each title is prefixed "[SEED]" so the
   delete-and-replace cycle is safe.
4. For three of those tasks (the two dedup targets plus one perf note),
   uploads the matching seed PDF to `lc_relateddocuments` via PATCH
   against `/api/data/v9.2/lc_tasks({id})/lc_relateddocuments`.

Prereqs:
- `.env` with DATAVERSE_URL pointing at the target environment.
- `az login --tenant <target tenant id>` against an account with
  Dataverse access on that env (System Customizer or higher).
- Q3 seed PDFs generated. Run `python scripts/generate_q3_seed_artifacts.py`
  first if `episodes/ep-07-scout-autopilot/seed-artifacts/` is empty.
- `lc_task` has the `lc_relateddocuments` File column with
  "Available for Search" turned on.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import get_token, load_env  # noqa: E402


LAUNCH_NAME = "Q3 Widget Launch"
TITLE_PREFIX = "[SEED] "
FILE_COLUMN = "lc_relateddocuments"

PRIORITY_HIGH = 10600402
PRIORITY_MEDIUM = 10600403
STATUS_NOT_STARTED = 10600301

ARTIFACT_DIR = (
    Path(__file__).resolve().parent.parent
    / "episodes"
    / "ep-07-scout-autopilot"
    / "seed-artifacts"
)


SEED_TASKS: list[dict] = [
    {
        "title": "Bug: Export to CSV crashes on >10-widget compositions",
        "notes": (
            "QA filed a blocker on the export path. Widget designer "
            "compositions with more than ten widgets hang for ~30s on "
            "Export to CSV and then crash the app. Owner: Platform. "
            "See attached repro. Severity: blocker."
        ),
        "priority": PRIORITY_HIGH,
        "attach": "q3-bug-export-crash.pdf",
    },
    {
        "title": "Bug: Pricing page disagrees with billing on Q3 promo tier",
        "notes": (
            "Pricing Ops filed an escalation. The promo page advertises "
            "$19; billing charges $24. Customer-facing pricing "
            "escalation, several inbound tickets already. Owner: "
            "Pricing Ops + Billing. See attached. Severity: high."
        ),
        "priority": PRIORITY_HIGH,
        "attach": "q3-bug-pricing-mismatch.pdf",
    },
    {
        "title": "Perf: first paint regressed from 380ms to 740ms",
        "notes": (
            "Perf team flagged a first-paint regression on the cold "
            "start path after the Q3 widget bundle was added. Not a "
            "blocker; on the watch list. See attached note."
        ),
        "priority": PRIORITY_MEDIUM,
        "attach": "q3-perf-regression.pdf",
    },
    {
        "title": "Docs: refresh release notes for Q3 widget set",
        "notes": (
            "Docs team owns the GA release notes draft. Needs a pass "
            "from PM before the marketing review."
        ),
        "priority": PRIORITY_MEDIUM,
    },
    {
        "title": "Marketing: build the Q3 widget launch landing page",
        "notes": (
            "Marketing site team to publish the Q3 widget launch "
            "landing page. Copy is in the brief, hero image pending."
        ),
        "priority": PRIORITY_MEDIUM,
    },
    {
        "title": "Sales enablement: Q3 widget battlecard",
        "notes": (
            "Field enablement to produce the Q3 widget battlecard and "
            "objection-handling FAQ before the seller kickoff."
        ),
        "priority": PRIORITY_MEDIUM,
    },
    {
        "title": "Security: signoff on Q3 widget telemetry payload",
        "notes": (
            "Security team to review the telemetry schema for the new "
            "widget bundle and sign off before GA."
        ),
        "priority": PRIORITY_MEDIUM,
    },
    {
        "title": "Localization: ship Q3 widget UI strings to FIGS",
        "notes": (
            "Loc team to ship FR/IT/DE/ES strings for the new widget "
            "designer surfaces. Source strings frozen on Friday."
        ),
        "priority": PRIORITY_MEDIUM,
    },
    {
        "title": "Support: Q3 widget runbook for tier-1 agents",
        "notes": (
            "Support to draft and publish the tier-1 runbook for the "
            "new widget designer. Tier-2 escalation criteria included."
        ),
        "priority": PRIORITY_MEDIUM,
    },
    {
        "title": "Legal: review widget asset license terms",
        "notes": (
            "Legal to confirm the third-party widget asset license "
            "terms cover GA distribution."
        ),
        "priority": PRIORITY_MEDIUM,
    },
]


def _headers(token: str, extra: dict | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def resolve_launch_id(env_url: str, token: str) -> str:
    print(f"Resolving '{LAUNCH_NAME}' ...")
    safe_name = LAUNCH_NAME.replace("'", "''")
    r = requests.get(
        f"{env_url}/api/data/v9.2/lc_launchs",
        params={"$select": "lc_launchid", "$filter": f"lc_name eq '{safe_name}' and statecode eq 0"},
        headers=_headers(token),
        timeout=60,
    )
    r.raise_for_status()
    rows = r.json().get("value", [])
    if not rows:
        raise RuntimeError(f"No launch named '{LAUNCH_NAME}' found.")
    lid = rows[0]["lc_launchid"]
    print(f"  -> launch id {lid}")
    return lid


def delete_prior_seed_tasks(env_url: str, token: str, launch_id: str) -> int:
    print("Removing any prior [SEED] tasks on this launch ...")
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
    rows = r.json().get("value", [])
    print(f"  found {len(rows)} prior seed tasks")
    for row in rows:
        tid = row["lc_taskid"]
        dr = requests.delete(
            f"{env_url}/api/data/v9.2/lc_tasks({tid})",
            headers=_headers(token),
            timeout=60,
        )
        if not dr.ok:
            print(f"  warning: delete {tid} -> {dr.status_code} {dr.text[:200]}")
    return len(rows)


def create_task(env_url: str, token: str, launch_id: str, spec: dict) -> str:
    body = {
        "lc_title": TITLE_PREFIX + spec["title"],
        "lc_notes": spec["notes"],
        "lc_priority": spec["priority"],
        "lc_taskstatus": STATUS_NOT_STARTED,
        "lc_launchid@odata.bind": f"/lc_launchs({launch_id})",
    }
    r = requests.post(
        f"{env_url}/api/data/v9.2/lc_tasks",
        headers=_headers(token, {"Prefer": "return=representation"}),
        json=body,
        timeout=60,
    )
    if not r.ok:
        raise RuntimeError(f"create lc_task failed: {r.status_code} {r.text[:500]}")
    return r.json()["lc_taskid"]


def attach_artifact(env_url: str, token: str, task_id: str, file_path: Path) -> None:
    data = file_path.read_bytes()
    r = requests.patch(
        f"{env_url}/api/data/v9.2/lc_tasks({task_id})/{FILE_COLUMN}",
        params={"x-ms-file-name": file_path.name},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        data=data,
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(
            f"attach {file_path.name} to {task_id} failed: {r.status_code} {r.text[:500]}"
        )


def main() -> int:
    load_env()
    env_url = os.environ.get("DATAVERSE_URL")
    if not env_url:
        print("DATAVERSE_URL not set in .env", file=sys.stderr)
        return 1
    env_url = env_url.rstrip("/")

    missing = [
        s["attach"]
        for s in SEED_TASKS
        if s.get("attach") and not (ARTIFACT_DIR / s["attach"]).exists()
    ]
    if missing:
        print("Missing seed artifacts:", file=sys.stderr)
        for m in missing:
            print(f"  - {ARTIFACT_DIR / m}", file=sys.stderr)
        print("Run: python scripts/generate_q3_seed_artifacts.py", file=sys.stderr)
        return 2

    token = get_token()
    launch_id = resolve_launch_id(env_url, token)
    delete_prior_seed_tasks(env_url, token, launch_id)

    created = 0
    attached = 0
    for spec in SEED_TASKS:
        tid = create_task(env_url, token, launch_id, spec)
        created += 1
        print(f"  + lc_task {tid}  {spec['title']}")
        if spec.get("attach"):
            attach_artifact(env_url, token, tid, ARTIFACT_DIR / spec["attach"])
            attached += 1
            print(f"      attached {spec['attach']} to {FILE_COLUMN}")

    print("")
    print(f"Seed done. Created {created} lc_task rows ({attached} with attached PDFs)")
    print(f"  Launch: {LAUNCH_NAME}  ({launch_id})")
    print(f"  Dedup targets for the on-camera sweep:")
    print(f"    - 'Bug: Export to CSV crashes ...'  matches sample-feedback.pdf")
    print(f"    - 'Bug: Pricing page disagrees ...' matches the seed email")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
