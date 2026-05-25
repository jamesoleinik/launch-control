"""Refresh the Dataverse MCP server's Authorization header in mcp-config.json.

Background
----------
The Copilot CLI's built-in OAuth flow for `DataverseMcporg40ae6a46` has been
producing access tokens that the Power Platform endpoint rejects with
`0x80095fcd: Guest user access is restricted` — even though the cached
refresh_token belongs to the correct Home identity
(`jamesol@a365preview001.onmicrosoft.com`).

Workaround: skip the CLI's OAuth machinery entirely. Mint a fresh access token
ourselves via a direct refresh_token grant, then write the token into the MCP
config as a static `Authorization: Bearer ...` header.

Usage
-----
    python scripts/python/refresh_dataverse_mcp_token.py

Re-run whenever the access token expires (every ~75 min) and then run
`/mcp` Reconnect (or restart the CLI) for it to pick up the new header.

State
-----
- First run: reads the refresh_token from the CLI's MCP OAuth cache file
  (bootstrap).
- Subsequent runs: reads/writes the rotating refresh_token from a side-channel
  state file at ~/.copilot/mcp-static-token-state.json so we never touch the
  CLI's own cache.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# --- Configuration -----------------------------------------------------------

SERVER_NAME = "DataverseMcporg40ae6a46"
SERVER_URL = "https://org40ae6a46.crm.dynamics.com/api/mcp_preview"
TENANT_ID = "adfa4542-3e1e-46f5-9c70-3df0b15b3f6c"  # a365preview001
CLIENT_ID = "aebc6443-996d-45c2-90f0-388ff96faa56"  # Visual Studio public client
SCOPE = (
    "https://org40ae6a46.crm.dynamics.com/api/mcp_preview/mcp.tools "
    "https://org40ae6a46.crm.dynamics.com/api/mcp_preview/user_impersonation "
    "offline_access"
)

# Bootstrap source: CLI's own MCP OAuth cache (read once, then never again)
BOOTSTRAP_CACHE_FILE = (
    Path.home()
    / ".copilot"
    / "mcp-oauth-config"
    / "721bda18a09945ac22b653264e931e64d93c3f0e42a6b1be3677e444b6f3375c.tokens.json"
)

# Our own state file: holds the rotating refresh_token between runs
STATE_FILE = Path.home() / ".copilot" / "mcp-static-token-state.json"

MCP_CONFIG_FILE = Path.home() / ".copilot" / "mcp-config.json"


# --- Helpers -----------------------------------------------------------------


def load_refresh_token() -> str:
    """Return the current refresh_token from STATE_FILE, else bootstrap from
    the CLI cache."""
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        rt = state.get("refresh_token")
        if rt:
            return rt
        print(f"WARNING: {STATE_FILE} exists but has no refresh_token; bootstrapping.")
    if not BOOTSTRAP_CACHE_FILE.exists():
        sys.exit(
            f"ERROR: state file is missing and bootstrap cache "
            f"{BOOTSTRAP_CACHE_FILE} is not present. Run the CLI's "
            f"`/mcp` Reconnect once first to populate the cache."
        )
    cache = json.loads(BOOTSTRAP_CACHE_FILE.read_text(encoding="utf-8"))
    rt = cache.get("refreshToken")
    if not rt:
        sys.exit(f"ERROR: no refreshToken in {BOOTSTRAP_CACHE_FILE}")
    return rt


def save_refresh_token(new_rt: str) -> None:
    payload = {
        "refresh_token": new_rt,
        "client_id": CLIENT_ID,
        "tenant_id": TENANT_ID,
        "scope": SCOPE,
        "updated": int(time.time()),
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def request_new_token(refresh_token: str) -> dict:
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPE,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"ERROR: AAD token endpoint returned {e.code}:\n{detail}")


def decode_jwt_claims(token: str) -> dict:
    import base64

    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    raw = base64.urlsafe_b64decode(payload.encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def update_mcp_config(access_token: str) -> None:
    if not MCP_CONFIG_FILE.exists():
        sys.exit(f"ERROR: {MCP_CONFIG_FILE} not found.")
    cfg = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
    servers = cfg.get("mcpServers") or {}
    entry = servers.get(SERVER_NAME)
    if entry is None:
        sys.exit(
            f"ERROR: server '{SERVER_NAME}' not found in {MCP_CONFIG_FILE}."
        )
    entry["headers"] = {"Authorization": f"Bearer {access_token}"}
    # Strip OAuth fields so the CLI does not silently reauthenticate over our
    # static header.
    entry.pop("oauthClientId", None)
    entry.pop("oauthPublicClient", None)
    # Atomic write
    tmp = MCP_CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    os.replace(tmp, MCP_CONFIG_FILE)


def main() -> None:
    refresh_token = load_refresh_token()
    print(f"[1/3] Got refresh_token (len={len(refresh_token)}). Calling AAD ...")
    resp = request_new_token(refresh_token)
    access_token = resp.get("access_token")
    new_refresh = resp.get("refresh_token", refresh_token)
    if not access_token:
        sys.exit(f"ERROR: no access_token in AAD response: {resp}")
    claims = decode_jwt_claims(access_token)
    exp_local = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(claims["exp"])))
    print(
        f"[2/3] New access_token: upn={claims.get('upn')} acct={claims.get('acct')} "
        f"scp='{claims.get('scp')}' aud={claims.get('aud')} exp={exp_local}"
    )
    save_refresh_token(new_refresh)
    update_mcp_config(access_token)
    print(f"[3/3] Wrote static Authorization header into {MCP_CONFIG_FILE}.")
    print(
        "\nNext: in Copilot CLI run /mcp -> Reconnect on "
        f"'{SERVER_NAME}', or restart the CLI."
    )


if __name__ == "__main__":
    main()
