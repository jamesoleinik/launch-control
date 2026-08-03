"""
setup_fabric_data_agent.py  --  Documents and verifies the Fabric Data Agent
configuration for Episode 10.

The Fabric Data Agent (preview) must be created in the Fabric portal. This script:
  1. Prints starter instructions to paste into the Fabric Data Agent portal.
  2. Verifies the agent exists in the LaunchControl workspace.
  3. Exports its item metadata for source control.

The Fabric Data Agent connects to the Lakehouse SQL analytics endpoint (NOT a
KQL Eventhouse). It queries T-SQL against these tables:
  - lc_statusupdate, lc_task, lc_launch, lc_vendorwork  (Dataverse via Fabric Link)
  - fno_vendtable, fno_vendtransopen                    (F&O via Fabric Link)
  - VendorEnrichment                                    (seeded by setup_lakehouse_tables.py)
  - ExternalVendorRisk                                  (seeded by setup_lakehouse_tables.py)

Usage:
    # Print portal setup instructions and schema hints:
    python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --instructions

    # List Fabric items in workspace (find the agent item ID):
    python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --list

    # Verify the agent exists and export its config:
    python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --verify

Portal creation steps (one-time, cannot be scripted):
    1. Go to https://fabric.microsoft.com and open the LaunchControl workspace.
    2. Click "+ New item" > "AI agent" (preview feature).
    3. Name: "LaunchControl Fabric Data Agent"
    4. Select data source: the LaunchControl Lakehouse (SQL analytics endpoint).
    5. Select tables: all 8 tables listed above.
    6. Paste the instructions from --instructions into the "Instructions" field.
    7. Add table descriptions (schema hints) from --instructions.
    8. Publish the agent.
    9. Note the agent item ID - needed for Copilot Studio connected-agent wiring.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402

WORKSPACE_ID = ""
FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"

AGENT_INSTRUCTIONS = """
You are an AI analyst connected to the LaunchControl Lakehouse - a unified data
layer that combines live Dataverse launch management data, F&O ERP vendor
transactions, internal vendor performance metrics (VendorEnrichment), and
external vendor risk intelligence from ProcureIQ (ExternalVendorRisk).

You answer questions about launch health, vendor risk, and anomaly detection
using the Lakehouse SQL analytics endpoint (T-SQL).

Key RED health value: lc_health = 10600603 (Red). AMBER = 10600602, GREEN = 10600601.
Always filter deleted rows: IsDelete = 0 OR IsDelete IS NULL.

When asked about vendor risk, join three sources for a full picture:
- VendorEnrichment (internal): on_time_pct, open_disputes, risk_tier
- ExternalVendorRisk (ProcureIQ): credit_rating, financial_health_score (0-100),
  market_risk_tier, diversity_certified
- fno_vendtransopen (F&O ERP): open invoice balance, overdue count

Join key: lc_vendorwork.lc_vendorref = VendorEnrichment.accountnum
          = ExternalVendorRisk.accountnum = fno_vendtransopen.accountnum

When asked about cross-launch patterns, aggregate lc_statusupdate grouped by
lc_launchidname to show RED/AMBER/GREEN distribution across all launches.

ExternalVendorRisk contains V0004 (Pacific Rim Components Ltd.) and V0005 (Nexus
Cloud Services Inc.) which are NOT referenced in any lc_vendorwork row. These
vendors exist in the external risk database but the operational system has not
engaged them. Mention this when relevant - it demonstrates that this analytics
layer holds risk signals Dataverse does not.
""".strip()

TABLE_DESCRIPTIONS = {
    "lc_statusupdate": (
        "Live Dataverse status updates from the Launch Control system. "
        "Each row is a health check-in for a launch. "
        "lc_health=10600603 means RED (at risk), 10600602=AMBER, 10600601=GREEN. "
        "lc_launchidname is the launch name. lc_taskidname is the associated task. "
        "createdon is when the update was written in Dataverse; "
        "SinkCreatedOn is when it arrived in Fabric via Fabric Link."
    ),
    "lc_launch": (
        "Launch master records from Dataverse. "
        "lc_code is the short identifier (e.g. EP11-DEMO-01). "
        "lc_launchstatus tracks lifecycle stage."
    ),
    "lc_task": (
        "Individual tasks within a launch. "
        "lc_taskstatus encodes task state. "
        "lc_duedate is the task deadline."
    ),
    "lc_vendorwork": (
        "Vendor work orders linked to launches. "
        "lc_vendorref is the vendor account number - join this to "
        "fno_vendtable.accountnum, VendorEnrichment.accountnum, "
        "and ExternalVendorRisk.accountnum. "
        "lc_committedamount and lc_invoicedamount track financial exposure."
    ),
    "fno_vendtable": (
        "F&O ERP vendor master. accountnum is the primary key. "
        "blocked=0 means active. creditmax is the approved credit limit."
    ),
    "fno_vendtransopen": (
        "F&O ERP open vendor transactions (unpaid invoices). "
        "amountmst is the amount in USD base currency. "
        "duedate is the payment due date."
    ),
    "VendorEnrichment": (
        "Internal vendor performance data seeded into the Lakehouse. "
        "on_time_pct is the historical on-time delivery rate (0-1). "
        "risk_tier is Low/Medium/High based on operational history. "
        "open_disputes is the count of unresolved delivery disputes. "
        "accountnum joins to lc_vendorwork.lc_vendorref."
    ),
    "ExternalVendorRisk": (
        "External market intelligence from ProcureIQ, a third-party procurement "
        "risk platform. This data is NOT in Dataverse or F&O - it exists only in "
        "this Lakehouse. financial_health_score is 0-100 (higher is healthier). "
        "market_risk_tier is Low/Medium/High/Critical. credit_rating uses standard "
        "notation (A, B+, C-, etc.). "
        "V0004 (Pacific Rim Components) and V0005 (Nexus Cloud Services) appear "
        "here but have no lc_vendorwork rows - they are on the risk watchlist but "
        "not yet engaged in any active launch."
    ),
}

EXAMPLE_QUERIES = {
    "RED updates in last 24h": """
SELECT lc_title, lc_launchidname, lc_taskidname, lc_health, createdon, SinkCreatedOn
FROM lc_statusupdate
WHERE lc_health = 10600603
  AND (IsDelete = 0 OR IsDelete IS NULL)
  AND createdon >= DATEADD(hour, -24, GETUTCDATE())
ORDER BY createdon DESC
""".strip(),

    "360-degree vendor risk for V0001": """
SELECT
    ve.accountnum, ve.vendor_name, ve.category,
    ve.on_time_pct, ve.open_disputes, ve.risk_tier,
    evr.credit_rating, evr.financial_health_score, evr.market_risk_tier,
    evr.diversity_certified,
    SUM(vto.amountmst) AS open_balance_usd,
    COUNT(vto.Id)      AS overdue_count,
    vt.blocked, vt.creditmax
FROM VendorEnrichment ve
LEFT JOIN ExternalVendorRisk evr ON ve.accountnum = evr.accountnum
LEFT JOIN fno_vendtransopen vto  ON ve.accountnum = vto.accountnum
    AND (vto.IsDelete = 0 OR vto.IsDelete IS NULL)
LEFT JOIN fno_vendtable vt       ON ve.accountnum = vt.accountnum
    AND (vt.IsDelete = 0 OR vt.IsDelete IS NULL)
WHERE ve.accountnum = 'V0001'
GROUP BY ve.accountnum, ve.vendor_name, ve.category, ve.on_time_pct,
         ve.open_disputes, ve.risk_tier, evr.credit_rating,
         evr.financial_health_score, evr.market_risk_tier, evr.diversity_certified,
         vt.blocked, vt.creditmax
""".strip(),

    "Cross-launch RED rate distribution": """
SELECT
    lc_launchidname AS launch_name,
    COUNT(*) AS total_updates,
    SUM(CASE WHEN lc_health = 10600603 THEN 1 ELSE 0 END) AS red_count,
    SUM(CASE WHEN lc_health = 10600602 THEN 1 ELSE 0 END) AS amber_count,
    SUM(CASE WHEN lc_health = 10600601 THEN 1 ELSE 0 END) AS green_count,
    ROUND(100.0 * SUM(CASE WHEN lc_health = 10600603 THEN 1 ELSE 0 END) / COUNT(*), 1) AS red_pct
FROM lc_statusupdate
WHERE IsDelete = 0 OR IsDelete IS NULL
GROUP BY lc_launchidname
ORDER BY red_pct DESC
""".strip(),

    "Vendors in risk DB but not in any launch": """
SELECT evr.accountnum, evr.vendor_name, evr.market_risk_tier,
       evr.financial_health_score, evr.credit_rating
FROM ExternalVendorRisk evr
WHERE NOT EXISTS (
    SELECT 1 FROM lc_vendorwork vw
    WHERE vw.lc_vendorref = evr.accountnum
      AND (vw.IsDelete = 0 OR vw.IsDelete IS NULL)
)
ORDER BY evr.financial_health_score ASC
""".strip(),
}


def _get_fabric_token() -> str:
    try:
        from azure.identity import AzureCliCredential
        cred = AzureCliCredential()
        return cred.get_token("https://api.fabric.microsoft.com/.default").token
    except Exception as e:
        raise RuntimeError(f"Could not get Fabric token: {e}")


def cmd_instructions() -> None:
    """Print the agent instructions and table descriptions ready to paste into the portal."""
    print("=" * 70)
    print("FABRIC DATA AGENT - INSTRUCTIONS (paste into 'Instructions' field)")
    print("=" * 70)
    print(AGENT_INSTRUCTIONS)
    print()
    print("=" * 70)
    print("TABLE DESCRIPTIONS (add one per table in the agent schema editor)")
    print("=" * 70)
    for table, desc in TABLE_DESCRIPTIONS.items():
        print(f"\n--- {table} ---")
        print(desc)
    print()
    print("=" * 70)
    print("EXAMPLE SQL QUERIES (for testing the agent in the Fabric portal)")
    print("=" * 70)
    for label, sql in EXAMPLE_QUERIES.items():
        print(f"\n--- {label} ---")
        print(sql)


def cmd_list(workspace_id: str) -> None:
    """List Fabric items in the workspace to find the Data Agent item ID."""
    import urllib.request
    token = _get_fabric_token()
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        items = data.get("value", [])
        data_agents = [i for i in items if i.get("type") in ("DataAgent", "AIAgent", "AISkill")]
        all_items = [(i.get("type"), i.get("displayName"), i.get("id")) for i in items]
        print(f"All items in workspace {workspace_id}:")
        for t, name, iid in sorted(all_items):
            marker = " <-- DATA AGENT" if t in ("DataAgent", "AIAgent", "AISkill") else ""
            print(f"  [{t}] {name}  ({iid}){marker}")
        if not data_agents:
            print("\nNo Data Agent items found. Create one in the Fabric portal first.")
            print("See --instructions for the portal creation steps.")
    except Exception as e:
        print(f"Error listing workspace items: {e}")


def cmd_verify(workspace_id: str) -> None:
    """Verify the Fabric Data Agent exists and export its metadata."""
    import urllib.request
    token = _get_fabric_token()
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        items = data.get("value", [])
        agents = [
            i for i in items
            if i.get("type") in ("DataAgent", "AIAgent", "AISkill")
            and "launch" in (i.get("displayName") or "").lower()
        ]
        if not agents:
            print("LaunchControl Fabric Data Agent NOT found in workspace.")
            print("Create it in the Fabric portal and re-run --verify.")
            return
        for agent in agents:
            print(f"Found: [{agent.get('type')}] {agent.get('displayName')}")
            print(f"  ID: {agent.get('id')}")
            print(f"  Description: {agent.get('description', '(none)')}")
            export_path = Path(__file__).parent / "fabric_data_agent_config.json"
            export_path.write_text(json.dumps(agent, indent=2))
            print(f"  Config exported to: {export_path.name}")
    except Exception as e:
        print(f"Error verifying workspace: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Document and verify the Fabric Data Agent for Episode 10."
    )
    parser.add_argument("--instructions", action="store_true",
                        help="Print portal setup instructions and schema hints")
    parser.add_argument("--list", action="store_true",
                        help="List Fabric items in the workspace")
    parser.add_argument("--verify", action="store_true",
                        help="Verify the Fabric Data Agent exists and export config")
    args = parser.parse_args()

    if args.instructions:
        cmd_instructions()
        return 0

    load_env("ep-10-dataverse-fabriciq")
    global WORKSPACE_ID
    WORKSPACE_ID = os.environ.get("FABRIC_WORKSPACE_ID", "")
    if not WORKSPACE_ID and (args.list or args.verify):
        print("ERROR: Set FABRIC_WORKSPACE_ID in .env")
        return 1

    if args.list:
        cmd_list(WORKSPACE_ID)
    elif args.verify:
        cmd_verify(WORKSPACE_ID)
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
