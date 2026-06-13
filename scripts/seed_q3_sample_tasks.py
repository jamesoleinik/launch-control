"""Seed Q3 Widget Launch with sample lc_task rows for the Ep-7 demo.

Why: Episode 7's Part 2 (the on-camera "run the sweep" beat) needs an
existing baseline of tasks on Q3 Widget Launch so that the skill's
dedup step (which uses the new MCP `search` tool over rows AND attached
files) is the visible value beat. Two of the seeded tasks are deliberate
dedup targets for the on-camera findings: the export-crash bug matches
`sample-feedback.pdf`, and the pricing-mismatch bug matches the seed
email. On-camera, those new findings should NOT create new tasks. They
should attach to the existing matching task and update its description.

What this script does:

1. Resolves the Q3 Widget Launch row via MCP `read_query`.
2. Creates ~10 sample `lc_task` rows on that launch via MCP
   `create_record`. Each task has lc_source = 'seed' so they're easy to
   clean up. A subset have lc_description and lc_name worded to be
   distinct from each other and from the on-camera findings except for
   the two intentional dedup targets.
3. For three of those tasks (the dedup targets plus one perf note), runs
   the file-upload trio against the task's file column to attach the
   matching seed PDF from `episodes/ep-07-scout-autopilot/seed-artifacts/`.

Re-running is safe-ish: the script first deletes any prior tasks on the
launch with lc_source = 'seed' before creating fresh ones, so the seed
is idempotent.

Prereqs:
- `.env` with DATAVERSE_URL set to the target environment.
- `az login --tenant <target tenant id>` against an account with
  Dataverse access on that env.
- `lc_task` has a file column with "Available for Search" turned on
  (the column name defaults to `lc_artifact`; override with the
  LC_TASK_FILE_COLUMN env var or edit the constant below).
- Q3 seed PDFs generated. Run `python scripts/generate_q3_seed_artifacts.py`
  first if `episodes/ep-07-scout-autopilot/seed-artifacts/` is empty.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import get_token, load_env  # noqa: E402


LAUNCH_NAME = "Q3 Widget Launch"
SOURCE_TAG = "seed"
LC_TASK_FILE_COLUMN = os.environ.get("LC_TASK_FILE_COLUMN", "lc_artifact")
ARTIFACT_DIR = (
    Path(__file__).resolve().parent.parent
    / "episodes"
    / "ep-07-scout-autopilot"
    / "seed-artifacts"
)


SEED_TASKS: list[dict] = [
    {
        "name": "Bug: Export to CSV crashes on >10-widget compositions",
        "description": (
            "QA filed a blocker on the export path. Widget designer "
            "compositions with more than ten widgets hang for ~30s on "
            "Export to CSV and then crash the app. Owner: Platform. "
            "See attached repro. Severity: blocker."
        ),
        "priority": "High",
        "status": "Open",
        "attach": "q3-bug-export-crash.pdf",
    },
    {
        "name": "Bug: Pricing page disagrees with billing on Q3 promo tier",
        "description": (
            "Pricing Ops filed an escalation. The promo page advertises "
            "$19; billing charges $24. Customer-facing pricing "
            "escalation, several inbound tickets already. Owner: "
            "Pricing Ops + Billing. See attached. Severity: high."
        ),
        "priority": "High",
        "status": "Open",
        "attach": "q3-bug-pricing-mismatch.pdf",
    },
    {
        "name": "Perf: first paint regressed from 380ms to 740ms",
        "description": (
            "Perf team flagged a first-paint regression on the cold "
            "start path after the Q3 widget bundle was added. Not a "
            "blocker; on the watch list. See attached note."
        ),
        "priority": "Normal",
        "status": "Open",
        "attach": "q3-perf-regression.pdf",
    },
    {
        "name": "Docs: refresh release notes for Q3 widget set",
        "description": (
            "Docs team owns the GA release notes draft. Needs a pass "
            "from PM before the marketing review."
        ),
        "priority": "Normal",
        "status": "Open",
    },
    {
        "name": "Marketing: build the Q3 widget launch landing page",
        "description": (
            "Marketing site team to publish the Q3 widget launch "
            "landing page. Copy is in the brief, hero image pending."
        ),
        "priority": "Normal",
        "status": "Open",
    },
    {
        "name": "Sales enablement: Q3 widget battlecard",
        "description": (
            "Field enablement to produce the Q3 widget battlecard and "
            "objection-handling FAQ before the seller kickoff."
        ),
        "priority": "Normal",
        "status": "Open",
    },
    {
        "name": "Security: signoff on Q3 widget telemetry payload",
        "description": (
            "Security team to review the telemetry schema for the new "
            "widget bundle and sign off before GA."
        ),
        "priority": "Normal",
        "status": "Open",
    },
    {
        "name": "Localization: ship Q3 widget UI strings to FIGS",
        "description": (
            "Loc team to ship FR/IT/DE/ES strings for the new widget "
            "designer surfaces. Source strings frozen on Friday."
        ),
        "priority": "Normal",
        "status": "Open",
    },
    {
        "name": "Support: Q3 widget runbook for tier-1 agents",
        "description": (
            "Support to draft and publish the tier-1 runbook for the "
            "new widget designer. Tier-2 escalation criteria included."
        ),
        "priority": "Normal",
        "status": "Open",
    },
    {
        "name": "Legal: review widget asset license terms",
        "description": (
            "Legal to confirm the third-party widget asset license "
            "terms cover GA distribution."
        ),
        "priority": "Normal",
        "status": "Open",
    },
]


def _rpc(env_url: str, token: str, method: str, params: dict, rpc_id: int) -> dict:
    url = f"{env_url.rstrip('/')}/api/mcp"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {"jsonrpc": "2.0", "id": rpc_id, "method": method, "params": params}
    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"{method} failed: {json.dumps(body['error'])}")
    return body["result"]


def _call_tool(env_url: str, token: str, name: str, arguments: dict, rpc_id: int) -> dict:
    result = _rpc(env_url, token, "tools/call",
                  {"name": name, "arguments": arguments}, rpc_id)
    if result.get("isError"):
        raise RuntimeError(f"tool {name} isError: {json.dumps(result, indent=2)}")
    for item in result.get("content", []):
        if item.get("type") == "text":
            text = item.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {}


def resolve_launch_id(env_url: str, token: str) -> str:
    print(f"Resolving '{LAUNCH_NAME}' via read_query ...")
    res = _call_tool(env_url, token, "read_query", {
        "query": (
            f"SELECT lc_launchid FROM lc_launch "
            f"WHERE lc_name = '{LAUNCH_NAME}' AND statecode = 0"
        )
    }, rpc_id=1)
    rows = res.get("rows") or res.get("value") or res.get("results") or []
    if not rows:
        raise RuntimeError(f"No launch named '{LAUNCH_NAME}' found.")
    row = rows[0]
    launch_id = row.get("lc_launchid") or row.get("lc_LaunchId") or row.get("id")
    if not launch_id:
        raise RuntimeError(f"read_query did not return a launch id: {row}")
    print(f"  -> launch id {launch_id}")
    return launch_id


def delete_prior_seed_tasks(env_url: str, token: str, launch_id: str) -> None:
    print("Removing any prior seed tasks on this launch ...")
    res = _call_tool(env_url, token, "read_query", {
        "query": (
            f"SELECT lc_taskid FROM lc_task "
            f"WHERE lc_launchid = '{launch_id}' AND lc_source = '{SOURCE_TAG}'"
        )
    }, rpc_id=2)
    rows = res.get("rows") or res.get("value") or res.get("results") or []
    print(f"  found {len(rows)} prior seed tasks")
    for i, row in enumerate(rows, start=10):
        tid = row.get("lc_taskid") or row.get("id")
        if not tid:
            continue
        try:
            _call_tool(env_url, token, "delete_record", {
                "tablename": "lc_task", "recordId": tid,
            }, rpc_id=i)
        except Exception as exc:
            print(f"  warning: delete_record on {tid} failed: {exc}")


def create_task(env_url: str, token: str, launch_id: str, spec: dict, rpc_id: int) -> str:
    res = _call_tool(env_url, token, "create_record", {
        "tablename": "lc_task",
        "columns": {
            "lc_name": spec["name"],
            "lc_description": spec["description"],
            "lc_priority": spec["priority"],
            "lc_status": spec["status"],
            "lc_source": SOURCE_TAG,
            "lc_launchid": {"relatedTable": "lc_launch", "recordId": launch_id},
        },
    }, rpc_id=rpc_id)
    tid = res.get("lc_taskid") or res.get("id") or res.get("recordId")
    if not tid:
        raise RuntimeError(f"create_record returned no id: {res}")
    return tid


def attach_artifact(env_url: str, token: str, task_id: str, file_path: Path, rpc_id: int) -> None:
    init = _call_tool(env_url, token, "init_file_upload", {
        "tablename": "lc_task",
        "recordId": task_id,
        "fileAttributeName": LC_TASK_FILE_COLUMN,
        "fileName": file_path.name,
    }, rpc_id=rpc_id)
    sas = init.get("sasUrl") or init.get("sas_url")
    cont = init.get("continuationToken") or init.get("continuation_token")
    if not (sas and cont):
        raise RuntimeError(f"init_file_upload missing fields: {init}")
    put = requests.put(sas, data=file_path.read_bytes(),
                       headers={"x-ms-blob-type": "BlockBlob",
                                "Content-Type": "application/pdf"}, timeout=60)
    put.raise_for_status()
    _call_tool(env_url, token, "commit_file_upload", {
        "continuationToken": cont, "fileName": file_path.name,
    }, rpc_id=rpc_id + 1)


def main() -> int:
    load_env()
    env_url = os.environ.get("DATAVERSE_URL")
    if not env_url:
        print("DATAVERSE_URL not set in .env", file=sys.stderr)
        return 1

    missing = [s["attach"] for s in SEED_TASKS
               if s.get("attach") and not (ARTIFACT_DIR / s["attach"]).exists()]
    if missing:
        print("Missing seed artifacts:", file=sys.stderr)
        for m in missing:
            print(f"  - {ARTIFACT_DIR / m}", file=sys.stderr)
        print("Run: python scripts/generate_q3_seed_artifacts.py", file=sys.stderr)
        return 2

    token = get_token()
    launch_id = resolve_launch_id(env_url, token)
    delete_prior_seed_tasks(env_url, token, launch_id)

    next_rpc = 100
    created = 0
    attached = 0
    for spec in SEED_TASKS:
        next_rpc += 1
        tid = create_task(env_url, token, launch_id, spec, next_rpc)
        created += 1
        print(f"  + lc_task {tid}  {spec['name']}")
        if spec.get("attach"):
            next_rpc += 2
            attach_artifact(env_url, token, tid, ARTIFACT_DIR / spec["attach"], next_rpc)
            attached += 1
            print(f"      attached {spec['attach']}")

    print("")
    print(f"Seed done. Created {created} lc_task rows ({attached} with attached PDFs)")
    print(f"  Launch: {LAUNCH_NAME}  ({launch_id})")
    print(f"  Dedup targets for the on-camera sweep:")
    print(f"    - 'Bug: Export to CSV crashes ...'  matches sample-feedback.pdf")
    print(f"    - 'Bug: Pricing page disagrees ...' matches the seed email")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
