"""Programmatically create a Copilot Studio "cliagent" declarative agent in Dataverse.

Authors a Copilot Studio agent the way the Episode 9 reconciliation agent is modeled:
one `bots` record (template `cliagent-1.0.0`) carrying the agent configuration
(model series, recognizer, instructions), plus one `botcomponents` record per MCP tool
(componenttype 9, an `McpTool`).

The tools are created deliberately UNCONNECTED (no `connectionReference`). A tool's
connection is an OAuth grant in the Power Platform connection service that only an
interactive sign-in can mint, so it cannot be written from a script. Creating the tools
without a reference makes them present as "not connected" in the Build canvas, so the
maker connects each tool once (Create new connection, sign in, Confirm) and then Publish.
If a tool were shipped with a pre-filled reference that has no live binding, the canvas
would think it is already connected and never prompt, and Preview would fail with
"missing connection reference(s)". So we leave them unconnected on purpose.

Dry-run first. Nothing is written unless you pass --apply.

Usage:
    python skills/copilot-studio-agent-authoring/create_agent.py \
        --name "Launch Control Reconciliation" \
        --instructions-file episodes/ep-09-dataverse-fno/assistive-agent-instructions.md \
        --dry-run

    # then, to write it:
    python skills/copilot-studio-agent-authoring/create_agent.py \
        --name "Launch Control Reconciliation" \
        --instructions-file episodes/ep-09-dataverse-fno/assistive-agent-instructions.md \
        --apply
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import string
import sys
from pathlib import Path


def find_root(start: Path) -> Path:
    p = start
    while p != p.parent:
        if (p / "scripts" / "auth.py").exists():
            return p
        p = p.parent
    raise SystemExit("Could not locate repo root (no scripts/auth.py found above this file).")


ROOT = find_root(Path(__file__).resolve())
sys.path.insert(0, str(ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402
import os  # noqa: E402
import requests  # noqa: E402

TEMPLATE = Path(__file__).with_name("references") / "agent-configuration.template.json"

# One entry per MCP tool. connector, the operation the tool invokes, and the labels the
# Copilot Studio UI uses for the botcomponent (kept ASCII: no em-dashes).
TOOLS = {
    "dataverse": {
        "connector": "shared_commondataserviceforapps",
        "operationId": "InvokeMCPPreview",
        "schema_key": "dvmcp",
        "tool_slug": "MicrosoftDataverse-MicrosoftDataverseMCPServerPrev",
        "display_name": "Microsoft Dataverse - Microsoft Dataverse MCP Server (Preview)",
        "description": "Provides Remote MCP Server access to Dataverse with preview tools",
    },
    "erp": {
        "connector": "shared_dynamicsax",
        "operationId": "InvokeMCP",
        "schema_key": "erpmcp",
        "tool_slug": "FinOpsAppsDynamics365-Dynamics365ERPMCP",
        "display_name": "Fin & Ops Apps (Dynamics 365) - Dynamics 365 ERP MCP",
        "description": "Provides Remote MCP Server access to Finance and Operations",
    },
}


def rand_suffix(n: int = 5) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def extract_instructions(path: Path) -> str:
    """Pull the agent instruction shell.

    If the file has a "## Instructions (paste verbatim)" section, return the text
    between that heading and the next "## " heading. Otherwise return the whole file.
    """
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^##\s+Instructions \(paste verbatim\)\s*\n", text, re.MULTILINE)
    if not m:
        return text.strip()
    start = m.end()
    nxt = re.search(r"^##\s+", text[start:], re.MULTILINE)
    body = text[start: start + nxt.start()] if nxt else text[start:]
    return body.strip()


def dv_get(base: str, headers: dict, url: str) -> dict:
    r = requests.get(base + url, headers=headers)
    r.raise_for_status()
    return r.json()


def build_bot_payload(schemaname: str, name: str, instructions: str) -> dict:
    cfg = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    cfg["agentSettings"]["instructions"]["segments"] = [
        {"$kind": "StaticSegment", "value": instructions}
    ]
    return {
        "name": name,
        "schemaname": schemaname,
        "template": "cliagent-1.0.0",
        "language": 1033,
        "authenticationmode": 2,
        "accesscontrolpolicy": 2,
        "configuration": json.dumps(cfg),
    }


def build_component_payload(bot_schema: str, bot_id: str, tool: dict) -> dict:
    # No connectionReference on purpose: the tool ships UNCONNECTED so the Build canvas
    # prompts the maker to connect it once (see module docstring).
    data = (
        "kind: McpTool\n"
        "authMode: Invoker\n"
        f"connectorId: /providers/Microsoft.PowerApps/apis/{tool['connector']}\n"
        f"operationId: {tool['operationId']}\n"
        "subToolSettings:\n"
        "toolInputs:\n"
    )
    schemaname = f"{bot_schema}.tool.{tool['schema_key']}_{rand_suffix(4)}"
    if len(schemaname) > 100:
        # Defensive: keep within the botcomponent schemaname limit.
        schemaname = schemaname[:100]
    payload = {
        "name": tool["display_name"],
        "schemaname": schemaname,
        "componenttype": 9,
        "description": tool["description"],
        "data": data,
    }
    if bot_id:
        payload["parentbotid@odata.bind"] = f"/bots({bot_id})"
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True, help="Display name for the agent")
    ap.add_argument("--instructions-file", required=True, help="Markdown/text file with the instruction shell")
    ap.add_argument("--schemaname", help="Full schema name (default: <prefix><slug>_<rand>)")
    ap.add_argument("--prefix", help="Publisher customization prefix (default: PUBLISHER_PREFIX from .env, else 'cr555')")
    ap.add_argument("--env", help="Episode env selector for scripts/auth (e.g. ep-09-dataverse-fno); default LC_ENV")
    ap.add_argument("--apply", action="store_true", help="Actually create the records (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    args = ap.parse_args()

    apply = args.apply and not args.dry_run

    load_env(args.env)
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    cred = get_credential(args.env)
    token = cred.get_token(env_url + "/.default").token
    base = f"{env_url}/api/data/v9.2"
    H = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    prefix = (args.prefix or os.environ.get("PUBLISHER_PREFIX") or "cr555").strip().rstrip("_")
    schemaname = args.schemaname or f"{prefix}_{slugify(args.name)}_{rand_suffix(5)}"
    instructions = extract_instructions(Path(ROOT / args.instructions_file if not Path(args.instructions_file).is_absolute() else args.instructions_file))
    if "\u2014" in instructions:
        raise SystemExit("Instruction text contains an em-dash (U+2014); remove it before authoring the agent.")

    print(f"Environment    : {env_url}")
    print(f"Agent name     : {args.name}")
    print(f"Schema name    : {schemaname}")
    print(f"Instructions   : {len(instructions)} chars from {args.instructions_file}")
    print("Tools          : Dataverse MCP + D365 F&O ERP MCP (created UNCONNECTED)")

    bot_payload = build_bot_payload(schemaname, args.name, instructions)

    if not apply:
        print("\n[dry-run] would POST /bots and two UNCONNECTED McpTool botcomponents.")
        print("[dry-run] pass --apply to create the records. Then connect each tool once")
        print("[dry-run] in the Build canvas and Publish (see the two steps printed on apply).")
        return 0

    r = requests.post(f"{base}/bots", headers=H, json=bot_payload)
    if r.status_code >= 400:
        print("POST /bots failed:", r.status_code, r.text[:1500])
        return 1
    bot = r.json()
    bot_id = bot["botid"]
    print(f"\nCreated bot {bot_id}")

    for key in ("dataverse", "erp"):
        comp = build_component_payload(schemaname, bot_id, TOOLS[key])
        rc = requests.post(f"{base}/botcomponents", headers=H, json=comp)
        if rc.status_code >= 400:
            print(f"POST /botcomponents ({key}) failed:", rc.status_code, rc.text[:1500])
            # Roll back the orphan bot so a re-run starts clean.
            dr = requests.delete(f"{base}/bots({bot_id})", headers=H)
            print(f"Rolled back bot {bot_id}: {dr.status_code}")
            return 1
        print(f"Created {key} tool component {rc.json()['botcomponentid']} (unconnected)")

    print("\nDone. Two manual steps remain in Copilot Studio (both by design, not scriptable):")
    print("  1. Open the agent in Build. Each of the two MCP tools shows as not connected.")
    print("     Open each tool, click Connect (Create new connection), sign in, and Confirm.")
    print("     The connection is an OAuth grant that only an interactive sign-in can mint,")
    print("     so it cannot be written from a script. A Preview error reading 'missing")
    print("     connection reference(s)' just means a tool has not been connected yet.")
    print("  2. Publish the agent once to make it live.")
    print(f"Agent: {env_url}  (schema {schemaname})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
