"""Drive the F&O (ERP) MCP server over stdio and (optionally) write a PO.

Unlike the Dataverse MCP server (a remote HTTP endpoint at ``<env>/api/mcp``),
the **Finance & Operations MCP server is hosted locally by the unified CLI**:

    dataverse mcp <fno-operations-url>

The CLI inspects the URL host and routes to Finance & Operations, then speaks MCP
over the child process's stdin/stdout. This script spawns that server and drives
it: ``initialize`` -> ``tools/list`` -> (with ``--write``) call a create tool to
add a purchase order in F&O.

Auth prerequisite
-----------------
The ERP MCP server authenticates through the unified CLI's own auth profile (an
MSAL token cache), not a bearer token you can pass in. Before running this, the
CLI must have an auth profile whose environment is THIS Dataverse/F&O
environment:

    dataverse auth create --environment <dataverse-url>
    # (device code:)  dataverse auth create --environment <dataverse-url> -dc

If no matching profile exists, the server blocks on interactive sign-in and this
script reports a clear "awaiting interactive auth" error (bounded, it will not
hang forever) with the CLI stderr, then exits non-zero. That is the expected
result in a headless/CI context; run it once interactively (or point it at a
profile created with a service principal) to get the live write.

Run:
    $env:PYTHONIOENCODING="utf-8"
    python episodes/ep-09-dataverse-fno/erp_mcp_write.py            # list tools
    python episodes/ep-09-dataverse-fno/erp_mcp_write.py --write    # create a PO
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth  # noqa: E402
from mcp_client import StdioMcp, McpError  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
DATA_AREA = "dat"
PO_NUMBER = "PO-10508"
VENDOR_ACCT = "V0003"

# Candidate F&O create tool + payload. The ERP MCP tool surface is discovered at
# runtime (printed by tools/list); adjust the tool name / args to match if the
# discovered names differ.
PO_PAYLOAD = {
    "dataAreaId": DATA_AREA,
    "PurchaseOrderNumber": PO_NUMBER,
    "OrderVendorAccountNumber": VENDOR_ACCT,
    "CurrencyCode": "USD",
    "LanguageId": "en-us",
    "PurchaseOrderName": "WIDGET-Q3 compliance attestation (Northwind), via ERP MCP",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="attempt to create a PO through an ERP MCP write tool")
    parser.add_argument("--auth-timeout", type=int, default=90,
                        help="seconds to wait for initialize before giving up")
    args = parser.parse_args()

    auth.load_env(EPISODE)
    fno_url = os.environ["FNO_URL"].rstrip("/")

    server_cmd = [
        "cmd", "/c", "npx", "-y", "@microsoft/dataverse@latest", "mcp", fno_url,
    ]
    print(f"ERP MCP server: dataverse mcp {fno_url}\n")

    try:
        with StdioMcp(server_cmd) as erp:
            info = erp.initialize(client_name="erp_mcp_write", timeout=args.auth_timeout)
            print(f"== initialize ==\n  server: {info.get('name')} "
                  f"v{info.get('version')}\n")

            tools = erp.list_tools()
            print(f"== tools/list ==\n  {len(tools)} tools: {', '.join(sorted(tools))}\n")

            if not args.write:
                print("Tool discovery only (pass --write to attempt a PO create).")
                return

            create_tool = next(
                (t for t in tools if "create" in t.lower()), None)
            if not create_tool:
                print("[FAIL] no create-style tool exposed by the ERP MCP server")
                raise SystemExit(1)

            print(f"== tools/call {create_tool}: create PO {PO_NUMBER} ==")
            out = erp.call(create_tool, {
                "tablename": "PurchaseOrderHeadersV2",
                "item": json.dumps(PO_PAYLOAD),
            })
            print(f"  {out[:400]}")
            print("\n[ok] ERP MCP write returned without error")
    except McpError as exc:
        print("== ERP MCP not reachable headless ==")
        print(f"  {exc}")
        print("\nThis is expected without a unified-CLI auth profile for this "
              "environment.\nCreate one, then re-run:")
        print("  dataverse auth create --environment "
              f"{os.environ['DATAVERSE_URL'].rstrip('/')} -dc")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
