#!/usr/bin/env python3
"""Read-only preflight for the 'Dataverse Accounts' Cowork plugin.

Checks the repo package wiring and that the target Dataverse environment is
reachable and exposes the account table for the signed-in user. It never
creates records, uploads packages, deploys plugins, or calls Cowork.

Usage:
  python preflight.py --plan      # print what it checks
  python preflight.py --run       # run the checks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DATAVERSE_URL = "https://org77c9659c.crm.dynamics.com"
ORGANIZATION_ID = "e616ec95-4b6b-f111-9bb1-000d3a31ff0e"
MCP_SUFFIX = "/api/mcp"

THIS_DIR = Path(__file__).resolve().parent
PKG_DIR = THIS_DIR.parent
MANIFEST_PATH = PKG_DIR / "manifest.json"
SKILL_PATH = PKG_DIR / "skills" / "list-my-accounts" / "SKILL.md"

PLAN = """# Dataverse Accounts - Cowork plugin preflight (read-only)

1. Package wiring
   - manifest.json parses.
   - agentConnectors[].remoteMcpServer.mcpServerUrl ends with /api/mcp.
   - authorization.type == OAuthPluginVault and a referenceId is set.
2. Business Skill
   - skills/list-my-accounts/SKILL.md exists and covers the account table.
3. Dataverse reachability (as the signed-in az user)
   - WhoAmI succeeds and OrganizationId matches the target org.
   - account table metadata is readable.
   - a top-1 read of accounts succeeds (read privilege present).
"""


class C:
    GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; END = "\033[0m"


def ok(msg: str) -> bool:
    print(f"  {C.GREEN}[PASS]{C.END} {msg}")
    return True


def warn(msg: str) -> bool:
    print(f"  {C.YELLOW}[WARN]{C.END} {msg}")
    return True


def fail(msg: str) -> bool:
    print(f"  {C.RED}[FAIL]{C.END} {msg}")
    return False


def dv_token() -> str:
    proc = subprocess.run(
        ["az", "account", "get-access-token", "--resource", DATAVERSE_URL,
         "--query", "accessToken", "-o", "tsv"],
        shell=True, text=True, capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(proc.stderr.strip() or "no token")
    return proc.stdout.strip()


def dv_get(path: str) -> tuple[int, dict | str]:
    tok = dv_token()
    req = urllib.request.Request(
        f"{DATAVERSE_URL}/api/data/v9.2/{path.lstrip('/')}",
        method="GET",
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json",
                 "OData-MaxVersion": "4.0", "OData-Version": "4.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def check_manifest() -> bool:
    print("\n[1] Package wiring")
    if not MANIFEST_PATH.exists():
        return fail(f"manifest not found: {MANIFEST_PATH}")
    try:
        mf = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return fail(f"manifest does not parse: {e}")
    connectors = mf.get("agentConnectors") or []
    if not connectors:
        return fail("manifest has no agentConnectors[]")
    src = connectors[0].get("toolSource", {}).get("remoteMcpServer", {})
    url = src.get("mcpServerUrl", "")
    auth = src.get("authorization", {})
    res = True
    res &= ok(f"mcpServerUrl = {url}") if url.endswith(MCP_SUFFIX) else fail(
        f"mcpServerUrl should end with {MCP_SUFFIX}: {url}")
    res &= ok("auth type OAuthPluginVault") if auth.get("type") == "OAuthPluginVault" else fail(
        f"auth type should be OAuthPluginVault: {auth.get('type')}")
    ref = auth.get("referenceId", "")
    if not ref:
        res &= fail("referenceId missing")
    elif ref == "__OAUTH_REFERENCE_ID__":
        warn("referenceId is still the placeholder (run build.ps1 -OAuthReferenceId to bake it in)")
    else:
        ok("referenceId set")
    return res


def check_skill() -> bool:
    print("\n[2] Business Skill")
    if not SKILL_PATH.exists():
        return fail(f"skill not found: {SKILL_PATH}")
    body = SKILL_PATH.read_text(encoding="utf-8").lower()
    return ok("skill covers the account table") if "account" in body else fail(
        "skill does not mention the account table")


def check_dataverse() -> bool:
    print("\n[3] Dataverse reachability")
    try:
        s, who = dv_get("WhoAmI")
    except Exception as e:
        return fail(f"could not acquire token / call WhoAmI: {e} (run az login)")
    if s != 200 or not isinstance(who, dict):
        return fail(f"WhoAmI HTTP {s}: {who}")
    if who.get("OrganizationId", "").lower() != ORGANIZATION_ID:
        return fail(f"OrganizationId mismatch: {who.get('OrganizationId')}")
    ok(f"WhoAmI org={who.get('OrganizationId')} user={who.get('UserId')}")

    s, meta = dv_get("EntityDefinitions(LogicalName='account')?$select=LogicalName,PrimaryNameAttribute")
    res = ok("account table metadata readable") if s == 200 else fail(
        f"account metadata HTTP {s}: {meta}")

    s, rows = dv_get("accounts?$select=name&$top=1")
    if s == 200:
        n = len(rows.get("value", [])) if isinstance(rows, dict) else 0
        ok(f"account read works (top-1 returned {n} row(s))")
    else:
        res &= fail(f"account read HTTP {s}: {rows}")
    return res


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args()
    if args.plan or not args.run:
        print(PLAN)
        if not args.run:
            return 0
    print("=" * 60)
    print("  Dataverse Accounts - Cowork plugin preflight")
    print("=" * 60)
    results = [check_manifest(), check_skill(), check_dataverse()]
    passed = all(results)
    print("\n" + "=" * 60)
    print(f"  {'ALL CHECKS PASSED' if passed else 'SOME CHECKS FAILED'}")
    print("=" * 60)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
