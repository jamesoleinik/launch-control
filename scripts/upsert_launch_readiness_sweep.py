"""Push the Launch Readiness Sweep business skill into Dataverse.

Calls the new Dataverse MCP server (`/api/mcp`) via JSON-RPC to:

1. `upsert_skill` — land the skill body from
   `business-skills/launch-readiness-sweep.md` into Dataverse.
2. `create_skill_resource` — register the same markdown as a linked
   resource on the skill so Scout's `describe` returns the canonical
   body alongside the skill metadata.
3. `init_file_upload` + HTTP PUT to SAS + `commit_file_upload` —
   actually upload the markdown bytes against the skill resource
   record.

Re-running this script updates the skill body in place
(`upsert_skill` is idempotent on `name`).

Requires `.env` with `DATAVERSE_URL` set. Auth uses the same
`scripts/auth.py` helper as the rest of the repo (Azure CLI by
default).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth import get_token, load_env  # noqa: E402

SKILL_NAME = "Launch Readiness Sweep"
SKILL_DESCRIPTION = (
    "Scheduled morning sweep. Pulls at-risk launches, dedups each "
    "finding against the launch's open lc_task rows via read_query "
    "(and file_download on any ambiguous candidate's attached "
    "collateral), enriches matches, files new lc_task rows for new "
    "findings, then posts one Teams summary. Designed to be the first "
    "step of a Microsoft Scout Automation."
)
SKILL_UNIQUE_NAME = "lc_launchreadinesssweep"
SKILL_BODY_PATH = (
    Path(__file__).resolve().parent.parent
    / "business-skills"
    / "launch-readiness-sweep.md"
)


def _rpc(env_url: str, token: str, method: str, params: dict, rpc_id: int) -> dict:
    """Call a JSON-RPC method against the Dataverse MCP server."""
    url = f"{env_url.rstrip('/')}/api/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": params,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    body = response.json()
    if "error" in body:
        raise RuntimeError(f"{method} failed: {json.dumps(body['error'])}")
    return body["result"]


def _call_tool(env_url: str, token: str, name: str, arguments: dict, rpc_id: int) -> dict:
    """Wrap `tools/call` to unwrap the standard MCP envelope."""
    result = _rpc(
        env_url,
        token,
        "tools/call",
        {"name": name, "arguments": arguments},
        rpc_id,
    )
    if result.get("isError"):
        raise RuntimeError(
            f"tool {name} returned isError: {json.dumps(result, indent=2)}"
        )
    content = result.get("content", [])
    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {}


def main() -> int:
    load_env()
    import os

    env_url = os.environ.get("DATAVERSE_URL")
    if not env_url:
        print("DATAVERSE_URL not set. Populate .env first.", file=sys.stderr)
        return 1

    body = SKILL_BODY_PATH.read_text(encoding="utf-8")
    token = get_token()

    print(f"Pushing '{SKILL_NAME}' to {env_url} via /api/mcp ...")
    upserted = _call_tool(
        env_url,
        token,
        "upsert_skill",
        {
            "name": SKILL_NAME,
            "description": SKILL_DESCRIPTION,
            "body": body,
            "uniquename": SKILL_UNIQUE_NAME,
        },
        rpc_id=1,
    )
    skill_id = (
        upserted.get("skillid")
        or upserted.get("id")
        or upserted.get("msdyn_aiskillid")
    )
    if not skill_id:
        print(f"upsert_skill returned no skill id: {upserted}", file=sys.stderr)
        return 2
    print(f"  -> skill id {skill_id}")

    resource_filename = SKILL_BODY_PATH.name
    print(f"Registering resource '{resource_filename}' ...")
    resource = _call_tool(
        env_url,
        token,
        "create_skill_resource",
        {
            "skillid": skill_id,
            "filename": resource_filename,
        },
        rpc_id=2,
    )
    resource_id = (
        resource.get("skillresourceid")
        or resource.get("id")
    )
    if not resource_id:
        print(f"create_skill_resource returned no resource id: {resource}", file=sys.stderr)
        return 3
    print(f"  -> resource id {resource_id}")

    print("Initiating file upload for the resource body ...")
    init = _call_tool(
        env_url,
        token,
        "init_file_upload",
        {
            "tablename": "skillresource",
            "recordId": resource_id,
            "fileAttributeName": "filecontent",
            "fileName": resource_filename,
        },
        rpc_id=3,
    )
    sas_url = init.get("sasUrl") or init.get("sas_url")
    continuation = init.get("continuationToken") or init.get("continuation_token")
    if not (sas_url and continuation):
        print(f"init_file_upload missing fields: {init}", file=sys.stderr)
        return 4

    print("Uploading bytes via PUT ...")
    put = requests.put(
        sas_url,
        data=body.encode("utf-8"),
        headers={
            "x-ms-blob-type": "BlockBlob",
            "Content-Type": "text/markdown",
        },
        timeout=60,
    )
    put.raise_for_status()

    print("Committing upload ...")
    _call_tool(
        env_url,
        token,
        "commit_file_upload",
        {
            "continuationToken": continuation,
            "fileName": resource_filename,
        },
        rpc_id=4,
    )

    print("")
    print("Done. Verify in Power Apps:")
    print("  - Tables -> Skill -> Launch Readiness Sweep")
    print("  - Related -> Skill Resources -> launch-readiness-sweep.md")
    print("")
    print("Then in Scout chat:")
    print('  "Find the launch readiness sweep skill in the Launch Control')
    print('   MCP server, describe it, and run it."')
    return 0


if __name__ == "__main__":
    sys.exit(main())
