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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth  # noqa: E402
from mcp_client import DataverseMcp  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
LAUNCH_CODE = "WIDGET-Q3"
# The seeder creates six base engagements; the write demo (write_fno.py) may add
# more, so assert "at least the base six" rather than an exact count.
MIN_ENGAGEMENTS = 6
CORE_TOOLS = {"read_query", "describe", "search", "create_record", "update_record"}


def main():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)
    print(f"Dataverse env: {url}")
    print(f"MCP endpoint : {url}/api/mcp\n")

    client = DataverseMcp(url, token)

    info = client.initialize(client_name="verify_mcp")
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
    query_ok = len(rows) >= MIN_ENGAGEMENTS
    print(
        f"\n  returned {len(rows)} engagements (>= {MIN_ENGAGEMENTS} expected): "
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
