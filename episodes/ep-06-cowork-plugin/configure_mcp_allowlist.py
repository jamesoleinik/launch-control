"""Phase D: configure Dataverse MCP allowlist for the Cowork demo.

Two writes:

  1. Enable the pre-installed 'Microsoft Cowork' row (currently isenabled=false).
     Cowork itself talks MCP to Dataverse on the user's behalf; this row has
     to be enabled or no Cowork plugin can talk to /api/mcp.

  2. Add LaunchControl-Cowork-MCP (the Entra app deploy.py just created) as a
     custom allowed MCP client.

Idempotent.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402


COWORK_CLIENT_NAME = "microsoftcowork"
MY_APP_NAME = "LaunchControl-Cowork-MCP"
MY_APP_UNIQUE = "lc_launchcontrolcoworkmcp"


def dv(method: str, path: str, body=None) -> tuple[int, dict | str]:
    load_env()
    dv_url = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = get_credential().get_token(f"{dv_url}/.default").token
    req = urllib.request.Request(
        f"{dv_url}/api/data/v9.2/{path.lstrip('/')}",
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        data=(json.dumps(body).encode() if body is not None else None),
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


def main() -> int:
    deploy_dir = REPO_ROOT / ".deploy" / "ep-06"
    latest = sorted(deploy_dir.glob("*.json"))[-1]
    artifacts = json.loads(latest.read_text())
    app_id = artifacts["entra"]["appId"]
    print(f"Latest deploy artifact: {latest.name}")
    print(f"My app ID:              {app_id}")

    # 1. Enable Microsoft Cowork row
    print(f"\n[1] Enable pre-installed '{COWORK_CLIENT_NAME}'")
    s, payload = dv("GET",
        f"allowedmcpclients?$select=allowedmcpclientid,name,isenabled&$filter=" +
        urllib.parse.quote(f"uniquename eq '{COWORK_CLIENT_NAME}'"))
    if s != 200 or not payload.get("value"):
        print(f"    WARN  could not find '{COWORK_CLIENT_NAME}' row: HTTP {s}")
    else:
        row = payload["value"][0]
        cw_id = row["allowedmcpclientid"]
        if row["isenabled"]:
            print(f"    OK  already enabled (id={cw_id})")
        else:
            s, _ = dv("PATCH", f"allowedmcpclients({cw_id})", {"isenabled": True})
            if s in (200, 204):
                print(f"    OK  enabled (id={cw_id})")
            else:
                print(f"    FAIL  HTTP {s}")
                return 1

    # 2. Add LaunchControl-Cowork-MCP as allowed MCP client
    print(f"\n[2] Add '{MY_APP_NAME}' to allowed MCP clients")
    s, payload = dv("GET",
        f"allowedmcpclients?$select=allowedmcpclientid,name,isenabled&$filter=" +
        urllib.parse.quote(f"applicationid eq '{app_id}'"))
    if s == 200 and payload.get("value"):
        row = payload["value"][0]
        if not row["isenabled"]:
            s, _ = dv("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
            print(f"    OK  existing row enabled (id={row['allowedmcpclientid']})")
        else:
            print(f"    OK  already present and enabled (id={row['allowedmcpclientid']})")
    else:
        s, payload = dv("POST", "allowedmcpclients", {
            "name": MY_APP_NAME,
            "uniquename": MY_APP_UNIQUE,
            "applicationid": app_id,
            "isenabled": True,
        })
        if s in (200, 201, 204):
            print(f"    OK  created (id={payload.get('allowedmcpclientid')})")
        else:
            print(f"    FAIL  HTTP {s}: {payload}")
            return 1

    # Re-list for confirmation
    print("\n[3] Final allowedmcpclients (isenabled only)")
    s, payload = dv("GET",
        "allowedmcpclients?$select=name,uniquename,applicationid,isenabled&$filter=" +
        urllib.parse.quote("isenabled eq true"))
    for r in payload.get("value", []):
        print(f"    [x] {r['name']:35s} app={r['applicationid']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
