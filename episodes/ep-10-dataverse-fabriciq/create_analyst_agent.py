"""
create_analyst_agent.py  --  Creates the Launch Analyst Copilot Studio agent
via the Dataverse bot entity API. This is Plane 2 of the Ep 10 architecture.

Creates a bot record with:
  - Display name: "Launch Analyst"
  - Instructions: ready to paste into the portal agent editor
  - Schema name: cr555_launchanalystagent (using env publisher prefix cr555)

Remaining portal steps after running this:
  1. Open the agent in Copilot Studio
  2. Add the Fabric Data Agent as a connected agent (Knowledge > Connected agents)
  3. Create the "Analyze RED launch" topic using analyst_agent_instructions.md
  4. Add Teams "Post message" action

Usage:
    python episodes/ep-10-dataverse-fabriciq/create_analyst_agent.py --apply
    python episodes/ep-10-dataverse-fabriciq/create_analyst_agent.py --dry-run
    python episodes/ep-10-dataverse-fabriciq/create_analyst_agent.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402

AGENT_SCHEMA_NAME = "cr555_launchanalystagent"
AGENT_DISPLAY_NAME = "Launch Analyst"
AGENT_DESCRIPTION = (
    "Plane 2 analytics agent for Episode 10. Receives a RED launch flag from "
    "Plane 1 (Launch Control agent), calls the Fabric Data Agent for cross-source "
    "vendor risk + anomaly analysis, and posts a Teams escalation."
)

AGENT_INSTRUCTIONS = """
You are the Launch Analyst, a proactive AI agent that detects and escalates launch health risks.

When you receive a launch ID (e.g. EP11-DEMO-01), you:
1. Ask the connected Fabric Data Agent: "Show me all RED health status updates for launch [launch_id] in the last 24 hours."
2. If none found: reply "No RED updates found for [launch_id]. No escalation needed."
3. For each RED update: ask "Give me the full vendor risk picture for the vendor linked to task [task_name] — include ProcureIQ credit rating, financial health score, market risk tier, on-time delivery, and open ERP balances."
4. Ask: "Is the RED health rate for [launch_id] an outlier vs. other launches?"
5. Compose a Teams alert with the findings and post it to the Launch Risk channel.
6. Reply to the caller with a 1-2 sentence summary.

You are grounded in Fabric data only. Never speculate beyond what the Fabric Data Agent returns.
""".strip()

# Minimal bot configuration JSON (CS will fill in more when opened in portal)
BOT_CONFIGURATION = json.dumps({
    "schemaVersion": "2.0.0",
    "kind": "Bot",
    "botFrameworkId": "",
    "description": AGENT_DESCRIPTION,
    "locale": "en-us",
    "authorizationOptions": {"authorizationMode": "None"},
    "topicTemplateId": ""
})


def _headers(tok: str) -> dict:
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }


def _find_existing(base: str, tok: str) -> dict | None:
    import urllib.parse
    filt = urllib.parse.quote(f"schemaname eq '{AGENT_SCHEMA_NAME}'")
    url = (base + f"/api/data/v9.2/bots"
           f"?$filter={filt}"
           f"&$select=name,botid,schemaname,publishedon")
    req = urllib.request.Request(url, headers=_headers(tok))
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    bots = data.get("value", [])
    return bots[0] if bots else None


def cmd_apply(base: str, tok: str, dry_run: bool) -> int:
    existing = None
    try:
        existing = _find_existing(base, tok)
    except Exception as e:
        print(f"Lookup error: {e}")

    if existing:
        print(f"[SKIP] Agent already exists: {existing['name']} (id={existing['botid']})")
        print(f"  Open in Copilot Studio to add the Fabric Data Agent connected agent.")
        return 0

    payload = {
        "name": AGENT_DISPLAY_NAME,
        "schemaname": AGENT_SCHEMA_NAME,
        "configuration": BOT_CONFIGURATION,
        "authenticationtrigger": 0,
    }

    if dry_run:
        print("[DRY RUN] Would POST to /api/data/v9.2/bots:")
        print(json.dumps({k: v for k, v in payload.items() if k != "configuration"}, indent=2))
        print(f"  schemaname: {AGENT_SCHEMA_NAME}")
        print(f"  Instructions will be set as the agent description/prompt.")
        return 0

    url = base + "/api/data/v9.2/bots"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        **_headers(tok),
        "Prefer": "return=representation",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.load(r)
        bot_id = result.get("botid", "?")
        print(f"[OK] Created agent: {AGENT_DISPLAY_NAME}")
        print(f"  botid     : {bot_id}")
        print(f"  schemaname: {AGENT_SCHEMA_NAME}")
        print()
        print("Next steps (portal):")
        print("  1. Open https://copilotstudio.microsoft.com")
        print("  2. Find 'Launch Analyst' and open it")
        print("  3. Knowledge > Add connected agent > select 'LaunchControl Fabric Data Agent'")
        print("  4. Add 'Analyze RED launch' topic from analyst_agent_instructions.md")
        print("  5. Add Teams 'Post message' action")
        print("  6. Publish the agent")
        return 0
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:400]
        print(f"[ERR] Create bot failed: HTTP {e.code} {msg}")
        return 1


def cmd_status(base: str, tok: str) -> int:
    existing = _find_existing(base, tok)
    if existing:
        print(f"Agent exists: {existing['name']}")
        print(f"  botid     : {existing['botid']}")
        print(f"  schemaname: {existing['schemaname']}")
        published = existing.get("publishedon")
        print(f"  published : {published or '(not yet published)'}")
        env_url = base.replace("https://", "").rstrip("/")
        print(f"  Studio URL: https://copilotstudio.microsoft.com")
    else:
        print(f"Agent '{AGENT_SCHEMA_NAME}' not found. Run --apply to create it.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Launch Analyst CS agent.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    load_env("ep-10-dataverse-fabriciq")
    base = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = __import__("scripts.auth", fromlist=["get_token"]).get_token("ep-10-dataverse-fabriciq")

    if args.status:
        return cmd_status(base, tok)
    if args.dry_run or args.apply:
        dry_run = not args.apply
        print(f"Dataverse : {base}")
        print(f"Agent     : {AGENT_DISPLAY_NAME} ({AGENT_SCHEMA_NAME})")
        print(f"Mode      : {'DRY RUN' if dry_run else 'APPLY'}")
        print()
        return cmd_apply(base, tok, dry_run)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
