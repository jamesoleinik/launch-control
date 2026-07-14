"""Drive the unified-CLI-hosted Dataverse MCP server over stdio.

The unified data CLI hosts an MCP server as a child process:

    dataverse mcp <url>

This is the **same Dataverse MCP server** the agent reaches over HTTP at
``<env>/api/mcp``; the CLI simply hosts it locally and speaks MCP over the child
process's stdin/stdout. This script spawns it and drives it: ``initialize`` ->
``tools/list`` -> (with ``--write``) call ``create_record`` to add a launch-side
row.

What the sign-in revealed about the tool surface
-------------------------------------------------
Pointing the CLI at the two URLs of a unified (F&O-linked) environment gives very
different results, confirmed live:

- ``dataverse mcp <dataverse-url>`` (``...crm.dynamics.com``) -> **15 tools**:
  ``read_query``, ``create_record``, ``update_record``, ``delete_record``,
  ``search``, ``create_table``/``update_table``/``delete_table``, ``describe``,
  the ``*_skill`` tools, and the file tools.
- ``dataverse mcp <fno-operations-url>`` (``...operations.dynamics.com``) ->
  **0 tools**.

So there is **no separate "F&O ERP MCP with form tools" hosted by this CLI**. The
CLI hosts the Dataverse MCP, and the operations URL exposes nothing. F&O data is
reached through that one server's ``read_query`` (the ``mserp_*`` virtual
entities) for reads; F&O **writes** go through the F&O OData API (see
``write_fno.py``), because a create through the Dataverse MCP virtual-entity path
is rejected by the platform ("Custom plugin execution is not allowed in nested
pipeline for Virtual Entity"). The form/config capability that can stand up a
legal entity's ledger lives in the interactive **Copilot Studio Dynamics 365 ERP
connector**, not in this CLI.

Auth prerequisite
-----------------
The CLI-hosted server authenticates through the unified CLI's own auth profile (an
MSAL token cache), not a bearer token you can pass in. Create a profile whose
environment is this Dataverse environment first:

    dataverse auth create --environment <dataverse-url>
    # (device code:)  dataverse auth create --environment <dataverse-url> -dc

Without a matching profile the server blocks on interactive sign-in and this
script reports a bounded "awaiting interactive auth" error, then exits non-zero.

Run:
    $env:PYTHONIOENCODING="utf-8"
    python episodes/ep-09-dataverse-fno/scripts/erp_mcp_write.py            # list tools
    python episodes/ep-09-dataverse-fno/scripts/erp_mcp_write.py --check-operations
    python episodes/ep-09-dataverse-fno/scripts/erp_mcp_write.py --write    # create an lc_ row
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth  # noqa: E402
from mcp_client import StdioMcp, McpError  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
DATA_AREA = "dat"

# A launch-side demo row created through the CLI-hosted Dataverse MCP create_record
# tool (a real, non-virtual custom table, so the nested-pipeline restriction that
# blocks F&O virtual-entity writes does not apply).
WORK_KEY = "WIDGET-Q3-VENDORWORK-ERPMCP"
ENGAGEMENT = {
    "lc_name": "ERP-MCP stdio demo engagement",
    "lc_workkey": WORK_KEY,
    "lc_launchcode": "WIDGET-Q3",
    "lc_vendoraccount": "V0003",
    "lc_vendorname": "Northwind Traders",
    "lc_ponumber": "PO-10508",
    "lc_committedamount": 18000,
    "lc_invoicedamount": 0,
    "lc_status": "PO open (not received)",
}


def _server_cmd(url):
    return ["cmd", "/c", "npx", "-y", "@microsoft/dataverse@latest", "mcp", url]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="create an lc_vendorwork row through create_record")
    parser.add_argument("--check-operations", action="store_true",
                        help="also point the CLI at the operations URL (0 tools)")
    parser.add_argument("--auth-timeout", type=int, default=120,
                        help="seconds to wait for initialize before giving up")
    args = parser.parse_args()

    auth.load_env(EPISODE)
    dv_url = os.environ["DATAVERSE_URL"].rstrip("/")
    fno_url = os.environ.get("FNO_URL", "").rstrip("/")

    print(f"CLI-hosted Dataverse MCP: dataverse mcp {dv_url}\n")

    try:
        with StdioMcp(_server_cmd(dv_url)) as dv:
            info = dv.initialize(client_name="erp_mcp_write", timeout=args.auth_timeout)
            print(f"== initialize ==\n  server: {info.get('name')} "
                  f"v{info.get('version')}\n")

            tools = dv.list_tools()
            print(f"== tools/list ==\n  {len(tools)} tools: {', '.join(sorted(tools))}\n")

            if args.check_operations and fno_url:
                print(f"== control: dataverse mcp {fno_url} ==")
                with StdioMcp(_server_cmd(fno_url)) as ops:
                    ops.initialize(client_name="erp_mcp_write_ops",
                                   timeout=args.auth_timeout)
                    ops_tools = ops.list_tools()
                    print(f"  {len(ops_tools)} tools (the operations URL hosts no "
                          f"tool surface)\n")

            if not args.write:
                print("Tool discovery only (pass --write to create an lc_ row).")
                return

            if "create_record" not in tools:
                print("[FAIL] create_record not exposed by the server")
                raise SystemExit(1)

            existing = dv.read_query(
                "SELECT lc_vendorworkid FROM lc_vendorwork "
                f"WHERE lc_workkey = '{WORK_KEY}'")
            if existing:
                print(f"[skip] engagement {WORK_KEY} already exists")
                return

            print(f"== tools/call create_record: lc_vendorwork {WORK_KEY} ==")
            dv.create_record("lc_vendorwork", dict(ENGAGEMENT))
            print(f"[ok] created lc_vendorwork {WORK_KEY} through the CLI-hosted "
                  f"Dataverse MCP")
    except McpError as exc:
        print("== CLI-hosted Dataverse MCP not reachable headless ==")
        print(f"  {exc}")
        print("\nThis is expected without a unified-CLI auth profile for this "
              "environment.\nCreate one, then re-run:")
        print("  dataverse auth create --environment "
              f"{dv_url} -dc")
        raise SystemExit(2)


if __name__ == "__main__":
    main()

