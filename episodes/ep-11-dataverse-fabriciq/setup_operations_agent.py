"""
setup_operations_agent.py -- Ep 11 Operations Agent automation helper.

The Operations Agent REST API schema is not fully documented. This script automates
the parts that are stable today:
1. list agents in a workspace
2. export an agent definition via getDefinition
3. create an agent from a captured definition JSON

Usage:
    python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --list
    python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --export --agent-id <id>
    python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --create --definition operations_agent_schema.json
    python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --update --agent-id <id> --definition operations_agent_schema.json

Prerequisites:
    - az login
    - LC_ENV=ep-11-dataverse-fabriciq or call with a valid .env
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402


API_ROOT = "https://api.fabric.microsoft.com/v1"
DEFAULT_EXPORT_PATH = "operations_agent_schema.json"


def _get_bearer_token() -> str:
    """Acquire a Fabric API token via AzureCliCredential, with az fallback."""
    try:
        from azure.identity import AzureCliCredential

        cred = AzureCliCredential(process_timeout=60)
        return cred.get_token("https://api.fabric.microsoft.com/.default").token
    except Exception:
        proc = subprocess.run(
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "https://api.fabric.microsoft.com",
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
        )
        token = proc.stdout.strip()
        if proc.returncode != 0 or not token:
            raise RuntimeError(f"Could not acquire Fabric token: {proc.stderr.strip()}")
        return token


def _fabric_request(
    method: str,
    path: str,
    token: str,
    body: dict | None = None,
) -> dict:
    """Call Fabric REST and return JSON (or empty dict for 204)."""
    url = f"{API_ROOT}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()
            if not payload:
                return {}
            return json.loads(payload.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Fabric API {method} {url} failed ({exc.code}): {raw}") from exc


def list_agents(workspace_id: str, token: str) -> None:
    result = _fabric_request("GET", f"/workspaces/{workspace_id}/operationsAgents", token)
    items = result.get("value", [])
    if not items:
        print("No Operations Agents found in workspace.")
        return
    print(f"Found {len(items)} Operations Agent(s):")
    for item in items:
        aid = item.get("id", "<no-id>")
        name = item.get("displayName", "<no-name>")
        state = item.get("state", "<unknown>")
        print(f"  {aid} | {name} | state={state}")


def export_definition(workspace_id: str, agent_id: str, token: str, out_path: Path) -> None:
    definition = _fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/operationsAgents/{agent_id}/getDefinition",
        token,
        body={},
    )
    out_path.write_text(json.dumps(definition, indent=2), encoding="utf-8")
    print(f"Exported definition to: {out_path}")

    # Also decode definition parts next to the export JSON for easy editing.
    container = definition.get("definition", {})
    parts = container.get("parts", [])
    if not parts:
        return
    parts_dir = out_path.parent / f"{out_path.stem}.parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for part in parts:
        path = part.get("path", "")
        payload = part.get("payload", "")
        if not path or not payload:
            continue
        target = parts_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(payload))
    print(f"Decoded definition parts to: {parts_dir}")


def create_from_definition(workspace_id: str, token: str, definition_path: Path) -> None:
    raw = json.loads(definition_path.read_text(encoding="utf-8"))

    # Fabric may accept different create payload shapes depending on preview version.
    candidate_bodies = []
    if "definition" in raw:
        candidate_bodies.append(raw)
        candidate_bodies.append(raw["definition"])
    else:
        candidate_bodies.append(raw)
        candidate_bodies.append({"definition": raw})

    last_error = None
    result = None
    for body in candidate_bodies:
        try:
            result = _fabric_request(
                "POST",
                f"/workspaces/{workspace_id}/operationsAgents",
                token,
                body=body,
            )
            break
        except Exception as exc:  # keep trying shape variants
            last_error = exc

    if result is None:
        raise RuntimeError(f"Create failed for all payload shapes. Last error: {last_error}")

    agent_id = result.get("id", "<unknown>")
    name = result.get("displayName", "<unknown>")
    print(f"Created Operations Agent: {name} ({agent_id})")


def update_from_definition(workspace_id: str, token: str, agent_id: str, definition_path: Path) -> None:
    raw = json.loads(definition_path.read_text(encoding="utf-8"))
    definition = raw.get("definition", raw)
    _fabric_request(
        "POST",
        f"/workspaces/{workspace_id}/operationsAgents/{agent_id}/updateDefinition",
        token,
        body={"definition": definition},
    )
    print(f"Updated Operations Agent definition: {agent_id}")


def render_template(
    workspace_id: str,
    kql_database_id: str,
    out_path: Path,
    recipient_upn: str,
) -> None:
    if not kql_database_id:
        raise RuntimeError("FABRIC_KQL_DATABASE_ID is required to render a template definition.")

    config = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/operationsAgents/definition/1.0.0/schema.json",
        "configuration": {
            "instructions": (
                "Watch RED launch status updates in Dataverse-linked KQL tables. "
                "When RED updates appear, summarize risk, include vendor context from "
                "VendorEnrichment, and send escalation text."
            ),
            "dataSources": {
                "launchcontrol": {
                    "id": kql_database_id,
                    "type": "KustoDatabase",
                    "workspaceId": workspace_id,
                }
            },
            "actions": {},
        },
        "playbook": {},
        "shouldRun": False,
    }
    if recipient_upn:
        config["configuration"]["messageDestination"] = {
            "kind": "Recipient",
            "recipient": recipient_upn,
        }

    out_path.write_text(json.dumps({"definition": config}, indent=2), encoding="utf-8")
    print(f"Wrote template definition: {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ep 11 Operations Agent setup helper.")
    parser.add_argument("--list", action="store_true", help="List Operations Agents in workspace")
    parser.add_argument("--export", action="store_true", help="Export agent definition from getDefinition")
    parser.add_argument("--create", action="store_true", help="Create Operations Agent from definition file")
    parser.add_argument("--update", action="store_true", help="Update existing Operations Agent from definition file")
    parser.add_argument(
        "--render-template",
        action="store_true",
        help="Render a starter Operations Agent definition using workspace + KQL DB IDs",
    )
    parser.add_argument("--agent-id", default="", help="Operations Agent ID (required for --export/--update)")
    parser.add_argument(
        "--definition",
        default=DEFAULT_EXPORT_PATH,
        help=f"Definition JSON path for --create / --export (default: {DEFAULT_EXPORT_PATH})",
    )
    parser.add_argument(
        "--recipient-upn",
        default="",
        help="Optional Teams recipient UPN to include in rendered template",
    )
    args = parser.parse_args()

    selected = [args.list, args.export, args.create, args.update, args.render_template]
    if sum(bool(x) for x in selected) != 1:
        parser.error("Choose exactly one action: --list, --export, --create, --update, or --render-template")

    load_env("ep-11-dataverse-fabriciq")
    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    kql_database_id = os.environ.get("FABRIC_KQL_DATABASE_ID", "").strip()
    if not workspace_id:
        print("ERROR: FABRIC_WORKSPACE_ID is required in .env")
        return 1

    definition_path = Path(args.definition)

    if args.render_template:
        render_template(workspace_id, kql_database_id, definition_path, args.recipient_upn.strip())
        return 0

    token = _get_bearer_token()

    if args.list:
        list_agents(workspace_id, token)
        return 0

    if args.export:
        if not args.agent_id:
            print("ERROR: --agent-id is required with --export")
            return 1
        export_definition(workspace_id, args.agent_id, token, definition_path)
        return 0

    if args.create:
        if not definition_path.exists():
            print(f"ERROR: Definition file not found: {definition_path}")
            return 1
        create_from_definition(workspace_id, token, definition_path)
        return 0

    if args.update:
        if not args.agent_id:
            print("ERROR: --agent-id is required with --update")
            return 1
        if not definition_path.exists():
            print(f"ERROR: Definition file not found: {definition_path}")
            return 1
        update_from_definition(workspace_id, token, args.agent_id, definition_path)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
