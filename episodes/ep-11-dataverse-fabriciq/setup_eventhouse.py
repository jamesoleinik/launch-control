"""
setup_eventhouse.py  --  Ep 11 Fabric eventhouse + KQL database setup.

Creates (or verifies) external Delta tables over the Dataverse Fabric Link
lakehouse, ingests the VendorEnrichment lookup table, and creates KQL
functions used by the Operations Agent rules.

Usage:
    # Dry-run (print commands, no changes):
    python episodes/ep-11-dataverse-fabriciq/setup_eventhouse.py --dry-run

    # Apply (idempotent):
    python episodes/ep-11-dataverse-fabriciq/setup_eventhouse.py --apply

Prerequisites:
    pip install azure-kusto-data azure-kusto-ingest

Auth:
    Uses 'az account get-access-token' (AzureCliCredential pattern).
    The cluster URI resource is the KQL cluster URI itself.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402

# ---------------------------------------------------------------------------
# Config  (actuals resolved from .env / environment variables at runtime)
# ---------------------------------------------------------------------------
WORKSPACE_ID    = ""   # filled at runtime from env
LAKEHOUSE_ID    = ""   # filled at runtime from env
CLUSTER_URI     = ""   # filled at runtime from env
INGEST_URI      = ""   # filled at runtime from env
KQL_DB          = ""   # filled at runtime from env
WS_NAME         = ""   # filled at runtime from env (FABRIC_WORKSPACE_NAME)
LH_NAME         = ""   # filled at runtime from env (FABRIC_LAKEHOUSE_NAME)

# OneLake Delta table root path pattern
ONELAKE_ROOT    = "abfss://{{ws}}@onelake.dfs.fabric.microsoft.com/{{lh}}.Lakehouse/Tables/{{tbl}};impersonate"

# ---------------------------------------------------------------------------
# Delta tables to expose in the KQL database as external tables.
# Schema is minimal (only columns used by Operations Agent rules + KQL fns).
# ---------------------------------------------------------------------------
EXTERNAL_TABLES = [
    {
        "name": "lc_statusupdate",
        "delta_table": "lc_statusupdate",
        "schema": (
            "Id:string, lc_statusupdateid:string, lc_title:string, "
            "lc_summary:string, lc_health:long, lc_postedat:datetime, "
            "createdon:datetime, SinkCreatedOn:datetime, IsDelete:bool, "
            "lc_launchidname:string, lc_taskidname:string, "
            "lc_launchid:string, lc_taskid:string"
        ),
    },
    {
        "name": "lc_task",
        "delta_table": "lc_task",
        "schema": (
            "Id:string, lc_taskid:string, lc_title:string, "
            "lc_taskstatus:long, lc_duedate:datetime, "
            "createdon:datetime, IsDelete:bool, "
            "lc_milestoneidname:string, lc_launchidname:string"
        ),
    },
    {
        "name": "lc_launch",
        "delta_table": "lc_launch",
        "schema": (
            "Id:string, lc_launchid:string, lc_name:string, "
            "lc_code:string, lc_targetdate:datetime, "
            "lc_launchstatus:long, createdon:datetime, IsDelete:bool"
        ),
    },
    {
        "name": "lc_vendorwork",
        "delta_table": "lc_vendorwork",
        "schema": (
            "Id:string, lc_vendorworkid:string, lc_name:string, "
            "lc_vendorref:string, lc_committedamount:real, "
            "lc_invoicedamount:real, lc_duedate:datetime, "
            "lc_porefname:string, createdon:datetime, IsDelete:bool"
        ),
    },
    {
        "name": "fno_vendtable",
        "delta_table": "vendtable",
        "schema": (
            "Id:string, accountnum:string, blocked:int, "
            "currency:string, vendgroup:string, "
            "creditmax:real, paymtermid:string, "
            "createdon:datetime, IsDelete:bool"
        ),
    },
    {
        "name": "fno_vendtransopen",
        "delta_table": "vendtransopen",
        "schema": (
            "Id:string, accountnum:string, amountcur:real, "
            "amountmst:real, duedate:datetime, "
            "createdon:datetime, IsDelete:bool"
        ),
    },
]

# ---------------------------------------------------------------------------
# VendorEnrichment — ingested directly into KQL (not from lakehouse).
# Adds human-readable vendor names and performance scores that aren't
# available in the F&O DirPartyTable (not linked to Fabric in this env).
# ---------------------------------------------------------------------------
VENDOR_ENRICHMENT_ROWS = [
    # accountnum, vendor_name,                category,              on_time_pct, open_disputes, risk_tier
    ("V0001", "Acme Translations Inc.",       "Localization",        0.61,        2,             "High"),
    ("V0002", "GlobalTech Licensing Ltd.",    "Software Licensing",  0.88,        0,             "Low"),
    ("V0003", "SwiftLogix Freight Co.",       "Logistics",           0.74,        1,             "Medium"),
]

VENDOR_ENRICHMENT_SCHEMA = (
    "accountnum:string, vendor_name:string, category:string, "
    "on_time_pct:real, open_disputes:int, risk_tier:string"
)

# ---------------------------------------------------------------------------
# KQL functions used by Operations Agent rule queries
# ---------------------------------------------------------------------------
KQL_FUNCTIONS = [
    {
        "name": "fn_live_red_updates",
        "body": """() {
    lc_statusupdate
    | where (IsDelete == false or isnull(IsDelete))
    | where lc_health == 10600603  // RED (eppcdemo1fno option set value)
    | order by SinkCreatedOn desc
}""",
        "doc": "Returns all live (non-deleted) RED health status updates, newest first.",
    },
    {
        "name": "fn_vendor_risk_for_blocker",
        "body": """(task_name:string) {
    lc_vendorwork
    | where (IsDelete == false or isnull(IsDelete))
    | where lc_name contains task_name or lc_porefname contains task_name
    | join kind=leftouter (
        fno_vendtransopen | where (IsDelete == false or isnull(IsDelete))
        | summarize open_balance_usd=sum(amountmst), overdue_count=count() by accountnum
    ) on $left.lc_vendorref == $right.accountnum
    | join kind=leftouter (
        VendorEnrichment
    ) on $left.lc_vendorref == $right.accountnum
    | project lc_name, lc_vendorref, vendor_name, category, risk_tier,
              on_time_pct, open_disputes, open_balance_usd, overdue_count,
              lc_committedamount, lc_invoicedamount, lc_duedate
}""",
        "doc": "Given a task name fragment, returns vendor financial + performance context.",
    },
    {
        "name": "fn_blocker_pattern_history",
        "body": """() {
    lc_statusupdate
    | where (IsDelete == false or isnull(IsDelete))
    | summarize
        total_updates=count(),
        red_count=countif(lc_health == 10600603),
        amber_count=countif(lc_health == 10600602),
        green_count=countif(lc_health == 10600601)
        by launch=lc_launchidname
    | extend red_pct = round(red_count * 100.0 / total_updates, 1)
    | order by red_pct desc
}""",
        "doc": "Cross-launch RED/AMBER/GREEN distribution for anomaly baseline.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_kusto_token(cluster_uri: str) -> str:
    try:
        from azure.identity import AzureCliCredential
        cred = AzureCliCredential()
        tok = cred.get_token(f"{cluster_uri}/.default").token
        return tok
    except Exception as e:
        raise RuntimeError(f"Could not get Kusto token via AzureCliCredential: {e}")


def _run_mgmt(client, db: str, cmd: str, dry_run: bool, label: str) -> bool:
    """Run a KQL management command, or print it in dry-run mode."""
    if dry_run:
        print(f"[DRY RUN] {label}")
        print(f"  {cmd[:120]}{'...' if len(cmd)>120 else ''}")
        return True
    try:
        client.execute_mgmt(db, cmd)
        print(f"[OK] {label}")
        return True
    except Exception as e:
        err = str(e)
        if "already exists" in err.lower() or "entityalreadyexists" in err.lower():
            print(f"[SKIP] {label} (already exists)")
            return True
        print(f"[ERR] {label}: {e}")
        return False


def _onelake_uri(ws_name: str, lh_name: str, tbl: str) -> str:
    return (
        f"abfss://{ws_name}@onelake.dfs.fabric.microsoft.com"
        f"/{lh_name}.Lakehouse/Tables/{tbl};impersonate"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Set up Ep 11 KQL database.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not args.apply:
        parser.print_help()
        return 1

    dry_run = not args.apply

    # Load env
    load_env("ep-11-dataverse-fabriciq")
    global WORKSPACE_ID, LAKEHOUSE_ID, CLUSTER_URI, INGEST_URI, KQL_DB
    WORKSPACE_ID    = os.environ.get("FABRIC_WORKSPACE_ID", "")
    LAKEHOUSE_ID    = os.environ.get("FABRIC_LAKEHOUSE_ID", "")
    CLUSTER_URI     = os.environ.get("FABRIC_KQL_CLUSTER_URI", "")
    INGEST_URI      = os.environ.get("FABRIC_KQL_INGEST_URI", "")
    KQL_DB          = os.environ.get("FABRIC_KQL_DATABASE_NAME", "LaunchControlEH")
    WS_NAME         = os.environ.get("FABRIC_WORKSPACE_NAME", "LaunchControl")
    LH_NAME         = os.environ.get("FABRIC_LAKEHOUSE_NAME", "")

    if not dry_run and not all([CLUSTER_URI, WS_NAME, LH_NAME]):
        print("ERROR: Set FABRIC_KQL_CLUSTER_URI, FABRIC_WORKSPACE_NAME, FABRIC_LAKEHOUSE_NAME in .env")
        return 1

    print(f"Cluster : {CLUSTER_URI or '(dry-run placeholder)'}")
    print(f"Database: {KQL_DB}")
    print(f"Mode    : {'DRY RUN' if dry_run else 'APPLY'}")
    print()

    # Connect
    client = None
    if not dry_run:
        from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
        tok = _get_kusto_token(CLUSTER_URI)
        kcsb = KustoConnectionStringBuilder.with_token_provider(CLUSTER_URI, lambda: tok)
        client = KustoClient(kcsb)

    ok = True

    # 1. External Delta tables
    print("=== External Delta tables ===")
    for tbl in EXTERNAL_TABLES:
        onelake = _onelake_uri(WS_NAME, LH_NAME, tbl["delta_table"])
        cmd = (
            f".create external table {tbl['name']} ({tbl['schema']}) "
            f"kind=delta "
            f"(h@'{onelake}')"
        )
        ok &= _run_mgmt(client, KQL_DB, cmd, dry_run, f"external table {tbl['name']}")

    # 2. VendorEnrichment native table + ingestion
    print()
    print("=== VendorEnrichment table ===")
    create_cmd = f".create-merge table VendorEnrichment ({VENDOR_ENRICHMENT_SCHEMA})"
    ok &= _run_mgmt(client, KQL_DB, create_cmd, dry_run, "create VendorEnrichment table")

    inline_data = "\n".join(
        f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]}"
        for r in VENDOR_ENRICHMENT_ROWS
    )
    mapping_cmd = (
        ".create-or-alter table VendorEnrichment ingestion csv mapping 'VendorEnrichmentCSV' "
        "'[{\"Column\":\"accountnum\",\"Ordinal\":0},{\"Column\":\"vendor_name\",\"Ordinal\":1},"
        "{\"Column\":\"category\",\"Ordinal\":2},{\"Column\":\"on_time_pct\",\"Ordinal\":3},"
        "{\"Column\":\"open_disputes\",\"Ordinal\":4},{\"Column\":\"risk_tier\",\"Ordinal\":5}]'"
    )
    ok &= _run_mgmt(client, KQL_DB, mapping_cmd, dry_run, "VendorEnrichment CSV mapping")
    ingest_cmd = f".ingest inline into table VendorEnrichment <|\n{inline_data}"
    # Check if already seeded (idempotent: skip if rows exist for all 3 vendors)
    if not dry_run and client:
        try:
            r_check = client.execute(KQL_DB, "VendorEnrichment | summarize n=count() | project n")
            existing = list(r_check.primary_results[0])[0][0] if r_check.primary_results[0] else 0
            if existing >= len(VENDOR_ENRICHMENT_ROWS):
                print(f"[SKIP] ingest VendorEnrichment rows (already has {existing} rows)")
            else:
                ok &= _run_mgmt(client, KQL_DB, ingest_cmd, dry_run, "ingest VendorEnrichment rows")
        except Exception:
            ok &= _run_mgmt(client, KQL_DB, ingest_cmd, dry_run, "ingest VendorEnrichment rows")
    else:
        ok &= _run_mgmt(client, KQL_DB, ingest_cmd, dry_run, "ingest VendorEnrichment rows")

    # 3. KQL functions
    print()
    print("=== KQL functions ===")
    for fn in KQL_FUNCTIONS:
        cmd = (
            f".create-or-alter function with (docstring='{fn['doc']}') "
            f"{fn['name']} {fn['body']}"
        )
        ok &= _run_mgmt(client, KQL_DB, cmd, dry_run, f"function {fn['name']}")

    # 4. Verify
    if not dry_run and client:
        print()
        print("=== Verification ===")
        try:
            resp = client.execute_mgmt(KQL_DB, ".show tables")
            tables = [row["TableName"] for row in resp.primary_results[0]]
            print(f"Tables in {KQL_DB}: {tables}")
            resp2 = client.execute_mgmt(KQL_DB, ".show external tables")
            ext_tables = [row["Name"] for row in resp2.primary_results[0]]
            print(f"External tables: {ext_tables}")
            resp3 = client.execute_mgmt(KQL_DB, ".show functions")
            fns = [row["Name"] for row in resp3.primary_results[0]]
            print(f"Functions: {fns}")
        except Exception as e:
            print(f"Verification error: {e}")
        client.close()

    print()
    print(f"Done. Status: {'OK' if ok else 'ERRORS - check output above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
