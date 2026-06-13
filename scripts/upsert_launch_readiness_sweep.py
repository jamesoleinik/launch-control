"""Push the Launch Readiness Sweep business skill into Dataverse.

Calls the new Dataverse MCP server (`/api/mcp_preview`) via JSON-RPC to:

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


def _rpc(env_url: str, token: str, method: str, params: dict, rpc_id, session_id: str | None = None) -> tuple[dict, str | None]:
    """Call a JSON-RPC method against the Dataverse MCP preview server.

    Returns (parsed_result, session_id). /api/mcp_preview requires an
    `initialize` handshake first; the server returns an `Mcp-Session-Id`
    response header that must be echoed on subsequent calls.
    """
    url = f"{env_url.rstrip('/')}/api/mcp_preview"
    payload: dict = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    if rpc_id is not None:
        payload["id"] = rpc_id
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    new_session = response.headers.get("Mcp-Session-Id") or session_id
    if not payload.get("id") and method.startswith("notifications/"):
        return ({}, new_session)
    # /api/mcp_preview returns SSE-framed responses ("data: {...}").
    text = response.text
    if text.startswith("event:") or "data:" in text[:64]:
        for line in text.splitlines():
            if line.startswith("data:"):
                text = line[5:].strip()
                break
    body = json.loads(text) if text else {}
    if "error" in body:
        raise RuntimeError(f"{method} failed: {json.dumps(body['error'])}")
    return (body.get("result", {}), new_session)


def _upload_via_webapi(env_url: str, token: str, resource_id: str, file_name: str, data: bytes) -> None:
    """Upload bytes into the `filecontent` file column on a skillresource record
    via the Dataverse Web API single-chunk path (works for files <128MB)."""
    url = (
        f"{env_url.rstrip('/')}/api/data/v9.2/skillresources({resource_id})"
        f"/filecontent?x-ms-file-name={file_name}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "x-ms-file-name": file_name,
    }
    r = requests.patch(url, headers=headers, data=data, timeout=60)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"Web API filecontent PATCH failed {r.status_code}: {r.text[:400]}")


def _init_session(env_url: str, token: str) -> str | None:
    """Best-effort MCP initialize handshake.

    /api/mcp_preview's `initialize` may return 403 in some tenants while
    `tools/call` still succeeds without an Mcp-Session-Id (the server
    appears to be lenient for the Azure CLI client today). We attempt
    init for protocol correctness and fall back to a sessionless call
    pattern if it fails.
    """
    try:
        _, sid = _rpc(
            env_url,
            token,
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "upsert_launch_readiness_sweep", "version": "0.2"},
            },
            rpc_id=1,
        )
    except requests.HTTPError as exc:
        print(f"  initialize handshake failed ({exc}); proceeding without Mcp-Session-Id")
        return None
    if sid:
        try:
            _rpc(env_url, token, "notifications/initialized", {}, rpc_id=None, session_id=sid)
        except requests.HTTPError:
            pass
    return sid


def _call_tool(env_url: str, token: str, name: str, arguments: dict, rpc_id: int, session_id: str) -> dict:
    """Wrap `tools/call` to unwrap the standard MCP envelope."""
    result, _ = _rpc(
        env_url,
        token,
        "tools/call",
        {"name": name, "arguments": arguments},
        rpc_id,
        session_id=session_id,
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

    print(f"Pushing '{SKILL_NAME}' to {env_url} via /api/mcp_preview ...")
    sid = _init_session(env_url, token)
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
        rpc_id=2,
        session_id=sid,
    )
    skill_id = (
        upserted.get("skillid")
        or upserted.get("SkillId")
        or upserted.get("id")
        or upserted.get("msdyn_aiskillid")
    )
    if not skill_id:
        print(f"upsert_skill returned no skill id: {upserted}", file=sys.stderr)
        return 2
    print(f"  -> skill id {skill_id}")

    resource_filename = SKILL_BODY_PATH.name
    print(f"Registering resource '{resource_filename}' ...")
    try:
        resource = _call_tool(
            env_url,
            token,
            "create_skill_resource",
            {
                "skillid": skill_id,
                "filename": resource_filename,
            },
            rpc_id=3,
            session_id=sid,
        )
        resource_id = (
            resource.get("skillresourceid")
            or resource.get("SkillResourceId")
            or resource.get("id")
        )
    except RuntimeError as exc:
        if "violates a database constraint" not in str(exc):
            raise
        print(f"  resource already exists; looking it up via Web API")
        lookup = requests.get(
            f"{env_url.rstrip('/')}/api/data/v9.2/skillresources?%24top=50",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30,
        )
        lookup.raise_for_status()
        match = next(
            (
                r for r in lookup.json().get("value", [])
                if r.get("filename") == resource_filename
                and (r.get("_skillid_value") == skill_id or r.get("skillid") == skill_id)
            ),
            None,
        )
        if not match:
            # Fall back to any resource with that filename.
            match = next(
                (r for r in lookup.json().get("value", []) if r.get("filename") == resource_filename),
                None,
            )
        if not match:
            raise RuntimeError("resource exists per MCP, but Web API lookup found none") from exc
        resource_id = match["skillresourceid"]
    if not resource_id:
        print(f"create_skill_resource returned no resource id: {resource}", file=sys.stderr)
        return 3
    print(f"  -> resource id {resource_id}")

    print("Initiating file upload for the resource body ...")
    init: dict = {}
    try:
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
            rpc_id=4,
            session_id=sid,
        )
    except (requests.HTTPError, RuntimeError) as exc:
        print(f"  init_file_upload failed via MCP ({exc}); falling back to Web API upload")
    sas_url = (
        init.get("sasUrl")
        or init.get("sas_url")
        or init.get("SasUrl")
    )
    continuation = (
        init.get("continuationToken")
        or init.get("continuation_token")
        or init.get("ContinuationToken")
        or init.get("FileContinuationToken")
    )
    if not (sas_url and continuation):
        # Fallback path: preview's init_file_upload occasionally returns 403
        # mid-session even when upsert_skill + create_skill_resource succeeded.
        # Drop down to the Dataverse Web API multi-chunk file upload for the
        # `filecontent` file column on the skillresource record.
        print(f"  init_file_upload unusable ({init}); falling back to Web API upload")
        _upload_via_webapi(env_url, token, resource_id, resource_filename, body.encode("utf-8"))
        print("")
        print("Done. Verify in Power Apps:")
        print("  - Tables -> Skill -> Launch Readiness Sweep")
        print("  - Related -> Skill Resources -> launch-readiness-sweep.md")
        return 0

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
            "fileContinuationToken": continuation,
            "fileName": resource_filename,
        },
        rpc_id=5,
        session_id=sid,
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
