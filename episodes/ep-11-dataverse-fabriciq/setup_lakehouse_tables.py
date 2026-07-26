"""
setup_lakehouse_tables.py  --  Ep 11 Fabric Lakehouse supplementary table setup.

Seeds VendorEnrichment and ExternalVendorRisk as Delta tables directly into the
Fabric Lakehouse via OneLake. These sit alongside the Fabric Link tables
(lc_statusupdate, lc_task, lc_launch, lc_vendorwork, fno_vendtable,
fno_vendtransopen) and are all queryable via the Lakehouse SQL analytics endpoint.

The Fabric Data Agent (Plane 2) points at this SQL endpoint — no KQL Eventhouse
needed.

Architecture:
    Dataverse (lc_* tables)  +  F&O (fno_* tables)
           ↓ Fabric Link (low-latency, ~11s median)
    Lakehouse (Delta Parquet on OneLake)
           + VendorEnrichment    (seeded by this script)
           + ExternalVendorRisk  (seeded by this script)
           ↓ SQL analytics endpoint
    Fabric Data Agent  →  natural-language queries
           ↓ connected agent
    Launch Analyst (Copilot Studio)  →  Teams alert

Usage:
    # Dry-run (print what would be written):
    python episodes/ep-11-dataverse-fabriciq/setup_lakehouse_tables.py --dry-run

    # Apply (idempotent: overwrites existing supplementary tables):
    python episodes/ep-11-dataverse-fabriciq/setup_lakehouse_tables.py --apply

    # Verify tables are visible in Lakehouse SQL endpoint:
    python episodes/ep-11-dataverse-fabriciq/setup_lakehouse_tables.py --verify

Prerequisites:
    pip install pandas pyarrow deltalake azure-identity

Auth:
    Uses AzureCliCredential (az login).
    OneLake path: abfss://<WorkspaceName>@onelake.dfs.fabric.microsoft.com/<LakehouseName>.Lakehouse/Tables/
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402

# ---------------------------------------------------------------------------
# Config  (filled at runtime from .env)
# ---------------------------------------------------------------------------
WS_NAME = ""   # FABRIC_WORKSPACE_NAME
LH_NAME = ""   # FABRIC_LAKEHOUSE_NAME
LH_ID   = ""   # FABRIC_LAKEHOUSE_ID  (for SQL endpoint verification)

# ---------------------------------------------------------------------------
# VendorEnrichment — internal vendor performance data.
# Source: operational launch management records.
# Covers vendors actively referenced in Dataverse lc_vendorwork rows.
# ---------------------------------------------------------------------------
VENDOR_ENRICHMENT = [
    # accountnum, vendor_name,                category,           on_time_pct, open_disputes, risk_tier
    ("V0001", "Acme Translations Inc.",        "Localization",     0.61, 2, "High"),
    ("V0002", "GlobalTech Licensing Ltd.",     "Software Licensing", 0.88, 0, "Low"),
    ("V0003", "SwiftLogix Freight Co.",        "Logistics",        0.74, 1, "Medium"),
]

# ---------------------------------------------------------------------------
# ExternalVendorRisk — third-party market and financial intelligence.
# Source: ProcureIQ procurement risk platform (fictional).
# This data does NOT live in Dataverse or F&O. It is the reason this Lakehouse
# exists as a multi-source layer rather than a simple Dataverse mirror.
#
# V0004 and V0005 are on the ProcureIQ watchlist but have no Dataverse
# lc_vendorwork rows — they are visible in Fabric only. This demonstrates
# that the analytics layer holds signals the operational system does not.
# ---------------------------------------------------------------------------
EXTERNAL_VENDOR_RISK = [
    # accountnum, vendor_name,               credit_rating, financial_health_score, market_risk_tier, diversity_certified, risk_source
    ("V0001", "Acme Translations Inc.",      "C",   38.0, "High",     False, "ProcureIQ"),
    ("V0002", "GlobalTech Licensing Ltd.",   "A",   82.0, "Low",      True,  "ProcureIQ"),
    ("V0003", "SwiftLogix Freight Co.",      "B+",  65.0, "Medium",   False, "ProcureIQ"),
    ("V0004", "Pacific Rim Components Ltd.", "B",   71.0, "Medium",   True,  "ProcureIQ"),
    ("V0005", "Nexus Cloud Services Inc.",   "C-",  29.0, "Critical", False, "ProcureIQ"),
]


def _onelake_path(ws_name: str, lh_name: str, table: str) -> str:
    return (
        f"abfss://{ws_name}@onelake.dfs.fabric.microsoft.com"
        f"/{lh_name}.Lakehouse/Tables/{table}"
    )


def _get_bearer_token() -> str:
    try:
        from azure.identity import AzureCliCredential
        cred = AzureCliCredential()
        return cred.get_token("https://storage.azure.com/.default").token
    except Exception as e:
        raise RuntimeError(f"Could not get OneLake bearer token: {e}")


def write_delta_table(path: str, df, token: str, dry_run: bool, label: str) -> bool:
    """Write a pandas DataFrame as a Delta table to OneLake."""
    if dry_run:
        print(f"[DRY RUN] {label}")
        print(f"  Path : {path}")
        print(f"  Rows : {len(df)}")
        print(f"  Cols : {list(df.columns)}")
        return True
    try:
        from deltalake import write_deltalake
        storage_options = {
            "bearer_token": token,
            "use_fabric_endpoint": "true",
        }
        write_deltalake(path, df, mode="overwrite", storage_options=storage_options)
        print(f"[OK] {label} ({len(df)} rows)")
        return True
    except Exception as e:
        print(f"[ERR] {label}: {e}")
        return False


def cmd_apply(dry_run: bool) -> int:
    import pandas as pd
    from datetime import datetime, timezone

    token = "" if dry_run else _get_bearer_token()

    ok = True

    # VendorEnrichment
    print("=== VendorEnrichment ===")
    ve_df = pd.DataFrame(
        VENDOR_ENRICHMENT,
        columns=["accountnum", "vendor_name", "category", "on_time_pct", "open_disputes", "risk_tier"],
    )
    path = _onelake_path(WS_NAME, LH_NAME, "VendorEnrichment")
    ok &= write_delta_table(path, ve_df, token, dry_run, "VendorEnrichment table")

    # ExternalVendorRisk
    print()
    print("=== ExternalVendorRisk (ProcureIQ) ===")
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    evr_df = pd.DataFrame(
        [(*r, as_of) for r in EXTERNAL_VENDOR_RISK],
        columns=[
            "accountnum", "vendor_name", "credit_rating",
            "financial_health_score", "market_risk_tier",
            "diversity_certified", "risk_source", "last_updated",
        ],
    )
    path = _onelake_path(WS_NAME, LH_NAME, "ExternalVendorRisk")
    ok &= write_delta_table(path, evr_df, token, dry_run, "ExternalVendorRisk table")

    if not dry_run:
        print()
        print("Tables written. They will appear in the Lakehouse SQL analytics endpoint")
        print("within a few minutes. Refresh the Lakehouse in Fabric to confirm.")
        print()
        print("Next: point the Fabric Data Agent at this Lakehouse SQL endpoint.")
        print("Run: python episodes/ep-11-dataverse-fabriciq/setup_fabric_data_agent.py --instructions")

    return 0 if ok else 1


def cmd_verify() -> int:
    """List tables visible in the Lakehouse via Fabric REST API."""
    import urllib.request
    import json

    try:
        from azure.identity import AzureCliCredential
        cred = AzureCliCredential()
        token = cred.get_token("https://api.fabric.microsoft.com/.default").token
    except Exception as e:
        print(f"Auth error: {e}")
        return 1

    ws_id = os.environ.get("FABRIC_WORKSPACE_ID", "")
    lh_id = os.environ.get("FABRIC_LAKEHOUSE_ID", "")
    if not ws_id or not lh_id:
        print("Set FABRIC_WORKSPACE_ID and FABRIC_LAKEHOUSE_ID in .env to verify.")
        return 1

    url = f"https://api.fabric.microsoft.com/v1/workspaces/{ws_id}/lakehouses/{lh_id}/tables"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        tables = data.get("data", [])
        print(f"Tables in Lakehouse ({lh_id}):")
        for t in tables:
            name = t.get("name", "?")
            ttype = t.get("type", "?")
            location = t.get("location", "")
            marker = " ✓" if name in ("VendorEnrichment", "ExternalVendorRisk") else ""
            print(f"  [{ttype}] {name}{marker}  {location}")
        missing = [
            t for t in ("VendorEnrichment", "ExternalVendorRisk")
            if not any(x.get("name") == t for x in tables)
        ]
        if missing:
            print(f"\nMissing tables: {missing}")
            print("Run --apply to seed them.")
        else:
            print("\nAll supplementary tables present.")
    except Exception as e:
        print(f"Error listing tables: {e}")
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed Lakehouse supplementary tables for Episode 11."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    load_env("ep-11-dataverse-fabriciq")
    global WS_NAME, LH_NAME, LH_ID
    WS_NAME = os.environ.get("FABRIC_WORKSPACE_NAME", "LaunchControl")
    LH_NAME = os.environ.get("FABRIC_LAKEHOUSE_NAME", "")
    LH_ID   = os.environ.get("FABRIC_LAKEHOUSE_ID", "")

    if args.verify:
        return cmd_verify()
    if args.dry_run or args.apply:
        if not args.dry_run and not LH_NAME:
            print("ERROR: Set FABRIC_LAKEHOUSE_NAME in .env")
            return 1
        print(f"Workspace: {WS_NAME}")
        print(f"Lakehouse: {LH_NAME or '(dry-run placeholder)'}")
        print(f"Mode     : {'DRY RUN' if args.dry_run else 'APPLY'}")
        print()
        return cmd_apply(dry_run=args.dry_run)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
