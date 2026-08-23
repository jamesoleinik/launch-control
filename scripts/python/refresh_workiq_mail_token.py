"""Refresh the WorkIQ-Mail-MCP-Server Authorization header in mcp-config.json.

Same workaround as refresh_dataverse_mcp_token.py, but targets the WorkIQ Mail
tools server (agent365). The Copilot CLI's OAuth session for the WorkIQ mail
server lapses and the write-capable mail tools drop out of the running session;
the generic WorkIQ token that remains is read-only for mail. This mints a fresh
access token from the cached refresh token and writes it as a static
`Authorization: Bearer` header so the server reconnects authenticated.

Usage
-----
    $env:WORKIQ_TENANT_ID="<tenant-id>"
    $env:WORKIQ_CLIENT_ID="<public-client-id>"
    python scripts/python/refresh_workiq_mail_token.py

Then in Copilot CLI run `/mcp` -> Reconnect on 'WorkIQ-Mail-MCP-Server'
(or restart the CLI) for it to pick up the new header.

State
-----
- First run: bootstraps the refresh_token from the newest CLI MCP OAuth cache
  file whose scope contains 'mcp_MailTools'.
- Subsequent runs: reads/writes the rotating refresh_token from
  ~/.copilot/mcp-mail-token-state.json.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SERVER_NAME = "WorkIQ-Mail-MCP-Server"
TENANT_ID = os.environ.get("WORKIQ_TENANT_ID", "")
CLIENT_ID = os.environ.get("WORKIQ_CLIENT_ID", "")

OAUTH_CACHE_DIR = Path.home() / ".copilot" / "mcp-oauth-config"
STATE_FILE = Path.home() / ".copilot" / "mcp-mail-token-state.json"
MCP_CONFIG_FILE = Path.home() / ".copilot" / "mcp-config.json"


def _newest_mail_cache():
    """Return (refresh_token, scope_str) from the newest MailTools token cache
    that carries a refresh token."""
    best = None
    for p in glob.glob(str(OAUTH_CACHE_DIR / "*.tokens.json")):
        try:
            o = json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(o, dict):
            continue
        scope = str(o.get("scope") or o.get("scopes") or "")
        rt = o.get("refreshToken") or o.get("refresh_token")
        if "mcp_MailTools" not in scope or not rt:
            continue
        mtime = os.path.getmtime(p)
        if best is None or mtime > best[0]:
            best = (mtime, rt, scope)
    if best is None:
        return None, None
    return best[1], best[2]


def load_refresh_and_scope():
    if STATE_FILE.exists():
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        rt = st.get("refresh_token")
        sc = st.get("scope")
        if rt and sc:
            return rt, sc
    rt, sc = _newest_mail_cache()
    if not rt:
        sys.exit(
            "ERROR: no MailTools token cache with a refresh_token found. "
            "Run the CLI's `/mcp` Reconnect on WorkIQ-Mail-MCP-Server once first."
        )
    return rt, sc


def build_scope(cache_scope: str) -> str:
    scopes = [s for s in cache_scope.split() if s.startswith("http")]
    if "offline_access" not in scopes:
        scopes.append("offline_access")
    return " ".join(scopes)


def request_new_token(refresh_token: str, scope: str) -> dict:
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    body = urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": scope,
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


def decode_claims(token: str) -> dict:
    import base64

    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload.encode("ascii")).decode("utf-8"))


def update_mcp_config(access_token: str) -> None:
    cfg = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
    servers = cfg.get("mcpServers") or {}
    entry = servers.get(SERVER_NAME)
    if entry is None:
        sys.exit(f"ERROR: server '{SERVER_NAME}' not found in {MCP_CONFIG_FILE}.")
    entry["headers"] = {"Authorization": f"Bearer {access_token}"}
    entry.pop("oauthClientId", None)
    entry.pop("oauthPublicClient", None)
    tmp = MCP_CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    os.replace(tmp, MCP_CONFIG_FILE)


def save_state(new_rt: str, scope: str) -> None:
    STATE_FILE.write_text(
        json.dumps(
            {
                "refresh_token": new_rt,
                "client_id": CLIENT_ID,
                "tenant_id": TENANT_ID,
                "scope": scope,
                "updated": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    missing = [
        name
        for name, value in (
            ("WORKIQ_TENANT_ID", TENANT_ID),
            ("WORKIQ_CLIENT_ID", CLIENT_ID),
        )
        if not value
    ]
    if missing:
        sys.exit("ERROR: missing configuration: " + ", ".join(missing))

    rt, cache_scope = load_refresh_and_scope()
    scope = build_scope(cache_scope)
    print(f"[1/3] refresh_token len={len(rt)}, {len(scope.split())} scopes. Calling AAD ...")
    resp = request_new_token(rt, scope)
    at = resp.get("access_token")
    new_rt = resp.get("refresh_token", rt)
    if not at:
        sys.exit(f"ERROR: no access_token in AAD response: {list(resp)}")
    c = decode_claims(at)
    exp_local = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(c["exp"])))
    print(
        f"[2/3] access_token: aud={c.get('aud')} tid={c.get('tid')} "
        f"scp_count={len(str(c.get('scp','')).split())} exp={exp_local}"
    )
    save_state(new_rt, cache_scope)
    update_mcp_config(at)
    print(f"[3/3] Wrote static Authorization header into {MCP_CONFIG_FILE} for '{SERVER_NAME}'.")
    print("\nNext: in Copilot CLI run /mcp -> Reconnect on "
          f"'{SERVER_NAME}', or restart the CLI.")


if __name__ == "__main__":
    main()
