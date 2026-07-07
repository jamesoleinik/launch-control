"""Interactive client for the Dynamics 365 ERP MCP server (streamable HTTP).

The ERP MCP server lives at ``<FNO_URL>/mcp`` and is gated by F&O's Allowed MCP
Clients list plus Entra OAuth. This script performs a device-code sign-in using a
pre-authorized public client id (the VS Code / GitHub Copilot client), then speaks
the Model Context Protocol over streamable HTTP to initialize the session and list
the available tools.

Resolve the environment from ``.env`` (LC_ENV); nothing here is hardcoded.

Usage:
    python erp_mcp_http.py            # sign in, initialize, list tools
    python erp_mcp_http.py --list     # same as default
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import requests
import urllib3

urllib3.disable_warnings()

# Pre-authorized public client (VS Code / GitHub Copilot) present on F&O's default
# Allowed MCP Clients list. Public client: no secret, supports the device-code flow.
DEFAULT_CLIENT_ID = "aebc6443-996d-45c2-90f0-388ff96faa56"


def _load_env() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, os.pardir, os.pardir))
    sys.path.insert(0, os.path.join(root, "scripts"))
    import auth  # noqa: E402

    lc_env = os.environ.get("LC_ENV", "ep-09-dataverse-fno")
    auth.load_env(lc_env)
    fno = os.environ.get("FNO_URL", "").rstrip("/")
    if not fno:
        raise SystemExit("FNO_URL is not set in the environment .env")
    return fno


def _discover(fno: str) -> tuple[str, str]:
    """Return (authority, scope) from the OAuth protected-resource metadata."""
    meta = requests.get(
        fno + "/.well-known/oauth-protected-resource", timeout=60, verify=False
    ).json()
    authz = meta["authorization_servers"][0]
    authority = authz.split("/v2.0")[0].rstrip("/")
    scope = next(
        (s for s in meta.get("scopes_supported", []) if s.startswith("http")),
        fno + "/mcp/mcp.tools",
    )
    return authority, scope


def _cache_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, ".erp_token_cache.json")


def _sign_in(authority: str, scope: str) -> str:
    import msal

    client_id = os.environ.get("ERP_MCP_CLIENT_ID", DEFAULT_CLIENT_ID)
    cache = msal.SerializableTokenCache()
    cache_file = _cache_path()
    if os.path.exists(cache_file):
        cache.deserialize(open(cache_file, "r", encoding="utf-8").read())
    app = msal.PublicClientApplication(client_id, authority=authority, token_cache=cache)

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent([scope], account=accounts[0])
    if not result or "access_token" not in result:
        flow = app.initiate_device_flow(scopes=[scope])
        if "user_code" not in flow:
            raise SystemExit(
                "Failed to start device flow: " + json.dumps(flow, indent=2)
            )
        print("\n=== SIGN IN ===")
        print(flow["message"])
        print("===============\n", flush=True)
        result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise SystemExit(
            "Sign-in failed: "
            + result.get("error", "")
            + " "
            + result.get("error_description", "")
        )
    if cache.has_state_changed:
        with open(cache_file, "w", encoding="utf-8") as fh:
            fh.write(cache.serialize())
    print("Signed in as:", result.get("id_token_claims", {}).get("preferred_username"))
    return result["access_token"]


class ErpMcpHttp:
    """Minimal Model Context Protocol client over streamable HTTP."""

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.session_id: str | None = None

    def _headers(self) -> dict[str, str]:
        h = {
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    @staticmethod
    def _parse(resp: requests.Response) -> dict | None:
        ctype = resp.headers.get("Content-Type", "")
        if "text/event-stream" in ctype:
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    payload = line[len("data:") :].strip()
                    if payload and payload != "[DONE]":
                        return json.loads(payload)
            return None
        if resp.text.strip():
            return resp.json()
        return None

    def _rpc(self, method: str, params: dict | None = None, notify: bool = False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = str(uuid.uuid4())
        if params is not None:
            body["params"] = params
        resp = requests.post(
            self.url, headers=self._headers(), json=body, timeout=120, verify=False
        )
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid
        if resp.status_code >= 400:
            raise SystemExit(f"{method} -> HTTP {resp.status_code}: {resp.text[:400]}")
        if notify:
            return None
        return self._parse(resp)

    def initialize(self) -> dict | None:
        out = self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "launch-control", "version": "1.0"},
            },
        )
        self._rpc("notifications/initialized", notify=True)
        return out

    def list_tools(self) -> list[dict]:
        out = self._rpc("tools/list") or {}
        return out.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict | None:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})


def main() -> int:
    fno = _load_env()
    authority, scope = _discover(fno)
    print("Authority:", authority)
    print("Scope:    ", scope)
    token = _sign_in(authority, scope)

    client = ErpMcpHttp(fno + "/mcp", token)
    init = client.initialize()
    info = (init or {}).get("result", {}).get("serverInfo", {})
    print("\nConnected to:", info.get("name"), info.get("version"))
    print("Session:", client.session_id)

    args = sys.argv[1:]
    if args and args[0] == "--call":
        name = args[1]
        arguments = json.loads(args[2]) if len(args) > 2 else {}
        print(f"\nCalling {name} with {json.dumps(arguments)}")
        out = client.call_tool(name, arguments)
        print(json.dumps(out, indent=2)[:6000])
        return 0

    tools = client.list_tools()
    print(f"\n{len(tools)} tools:")
    for t in tools:
        print(" -", t.get("name"), ":", (t.get("description") or "").split("\n")[0][:80])
    return 0


if __name__ == "__main__":
    sys.exit(main())
