"""Verify the WIDGET-Q3 vendor-outsourcing model over the Dataverse MCP server.

This is the third proof for the "better together" join, complementing
``verify_vendorwork.py`` (raw OData + SQL/TDS). It exercises the *same*
``lc_vendorwork`` data through the Dataverse Model Context Protocol (MCP)
endpoint, the way a Copilot Studio or VS Code agent reaches the environment:

1. ``initialize`` the MCP session over streamable HTTP and capture the
   ``Mcp-Session-Id``.
2. ``tools/list`` and assert the core tools (``read_query``, ``describe``,
   ``search``) are present.
3. ``tools/call`` ``read_query`` to pull the launch-to-procurement join and a
   GROUP BY vendor rollup, then assert all six WIDGET-Q3 engagements come back.

The MCP endpoint is only reachable once a Power Platform admin has enabled the
Dataverse MCP server for the environment and allowlisted the calling client app
(Power Platform admin center > Environment > Settings > Product > Features >
Dataverse Model Context Protocol). See:
https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-disable

Run:
    $env:PYTHONIOENCODING="utf-8"
    python episodes/ep-09-dataverse-fno/verify_mcp.py
"""

import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
LAUNCH_CODE = "WIDGET-Q3"
EXPECTED_ENGAGEMENTS = 6
CORE_TOOLS = {"read_query", "describe", "search", "create_record", "update_record"}


class McpClient:
    """Minimal streamable-HTTP JSON-RPC client for the Dataverse MCP server."""

    def __init__(self, base_url, token):
        self.url = f"{base_url.rstrip('/')}/api/mcp"
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        self._id = 0

    @staticmethod
    def _parse(resp):
        if "text/event-stream" in resp.headers.get("Content-Type", ""):
            payload = None
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    try:
                        payload = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        pass
            return payload
        return resp.json()

    def _rpc(self, method, params=None, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if not notify:
            self._id += 1
            body["id"] = self._id
        if params is not None:
            body["params"] = params
        resp = self.session.post(
            self.url, headers=self.headers, data=json.dumps(body), timeout=120
        )
        resp.raise_for_status()
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.headers["Mcp-Session-Id"] = sid
        if notify:
            return None
        return self._parse(resp)

    def initialize(self):
        res = self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "verify_mcp", "version": "1.0"},
            },
        )
        self._rpc("notifications/initialized", notify=True)
        return (res or {}).get("result", {}).get("serverInfo", {})

    def list_tools(self):
        res = self._rpc("tools/list")
        return [t["name"] for t in (res or {}).get("result", {}).get("tools", [])]

    def read_query(self, sql):
        res = self._rpc(
            "tools/call", {"name": "read_query", "arguments": {"querytext": sql}}
        )
        result = (res or {}).get("result")
        if result is None:
            raise RuntimeError(f"read_query failed: {json.dumps(res)[:400]}")
        text = "".join(
            c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"
        )
        return json.loads(text) if text.strip() else []


def main():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)
    print(f"Dataverse env: {url}")
    print(f"MCP endpoint : {url}/api/mcp\n")

    client = McpClient(url, token)

    info = client.initialize()
    print(f"== initialize ==\n  server: {info.get('name')} v{info.get('version')}\n")

    tools = client.list_tools()
    print(f"== tools/list ==\n  {len(tools)} tools: {', '.join(sorted(tools))}")
    missing = CORE_TOOLS - set(tools)
    tools_ok = not missing
    print(f"  core tools present: {'PASS' if tools_ok else 'FAIL (missing ' + ', '.join(sorted(missing)) + ')'}\n")

    print("== tools/call read_query: lc_vendorwork -> launch procurement join ==\n")
    rows = client.read_query(
        "SELECT lc_workkey, lc_vendorname, lc_vendoraccount, lc_ponumber, "
        "lc_committedamount, lc_invoicedamount, lc_status "
        f"FROM lc_vendorwork WHERE lc_launchcode = '{LAUNCH_CODE}' "
        "ORDER BY lc_ponumber"
    )
    for r in rows:
        print(
            f"  {r.get('lc_vendorname', '?'):26}{r.get('lc_vendoraccount', '?'):8}"
            f"{r.get('lc_ponumber', '?'):10}"
            f"{float(r.get('lc_committedamount') or 0):>9.0f}"
            f"{float(r.get('lc_invoicedamount') or 0):>9.0f}  {r.get('lc_status', '')}"
        )
    query_ok = len(rows) == EXPECTED_ENGAGEMENTS
    print(
        f"\n  returned {len(rows)}/{EXPECTED_ENGAGEMENTS} engagements: "
        f"{'PASS' if query_ok else 'FAIL'}\n"
    )

    print("== tools/call read_query: GROUP BY vendor rollup ==\n")
    rollup = client.read_query(
        "SELECT lc_vendorname, COUNT(*) AS engagements, "
        "SUM(lc_committedamount) AS committed, SUM(lc_invoicedamount) AS invoiced "
        "FROM lc_vendorwork GROUP BY lc_vendorname"
    )
    def vendor_name(row):
        # A GROUP BY column comes back table-qualified (lc_vendorwork_lc_vendorname).
        for key, value in row.items():
            if key.endswith("lc_vendorname"):
                return value
        return "?"

    for r in rollup:
        print(
            f"  {vendor_name(r):26} {r.get('engagements')} eng  "
            f"committed={float(r.get('committed') or 0):>9.0f}  "
            f"invoiced={float(r.get('invoiced') or 0):>9.0f}"
        )
    rollup_ok = len(rollup) > 0
    print(f"\n  rollup rows: {len(rollup)} ({'PASS' if rollup_ok else 'FAIL'})\n")

    print("== Result ==")
    print(f"  MCP tools present    : {'PASS' if tools_ok else 'FAIL'}")
    print(f"  MCP read_query join  : {'PASS' if query_ok else 'FAIL'}")
    print(f"  MCP GROUP BY rollup  : {'PASS' if rollup_ok else 'FAIL'}")

    if not (tools_ok and query_ok and rollup_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
