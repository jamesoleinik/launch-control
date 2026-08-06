"""
setup_lakehouse_tables.py  --  Ep 10 Fabric Lakehouse supplementary table setup.

Seeds VendorEnrichment and ExternalVendorRisk as managed Delta tables in the
Fabric Lakehouse. Writes the Delta tables directly to the OneLake Tables/
section via the deltalake writer (no Spark job), so it is not subject to the
Fabric Spark compute rate limit that the REST table-load API hits under
capacity contention. The tables then appear in the Lakehouse SQL analytics
endpoint and are visible to Spark SQL joins.

Architecture:
    Dataverse (lc_* tables)  +  F&O (fno_* tables)
           ↓ Fabric Link (low-latency sync)
    Lakehouse (Delta Parquet on OneLake)
           + VendorEnrichment    (seeded by this script)
           + ExternalVendorRisk  (seeded by this script)
           ↓ SQL analytics endpoint
    Direct Lake semantic model + Power BI report (no DAX authored by hand)

Usage:
    # Dry-run (print what would be written):
    python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --dry-run

    # Apply (idempotent: writes/overwrites the Delta tables):
    python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --apply

    # Verify tables are visible in Lakehouse SQL endpoint:
    python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --verify

Prerequisites:
    pip install deltalake pyarrow pandas azure-identity

Auth:
    Uses AzureCliCredential (az login).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WS_NAME = ""
WS_ID   = ""
LH_NAME = ""
LH_ID   = ""

FABRIC_API = "https://api.fabric.microsoft.com/v1"
ONELAKE_HOST = "onelake.dfs.fabric.microsoft.com"

# ---------------------------------------------------------------------------
# VendorEnrichment - internal vendor performance data.
# ---------------------------------------------------------------------------
VENDOR_ENRICHMENT_HEADER = "accountnum,vendor_name,category,on_time_pct,open_disputes,risk_tier"
VENDOR_ENRICHMENT_ROWS = [
    "V0001,Contoso Supply Co,Components,0.61,2,High",
    "V0002,Fabrikam Media,Creative,0.88,0,Low",
    "V0003,SwiftLogix Freight Co.,Logistics,0.74,1,Medium",
]

# ---------------------------------------------------------------------------
# ExternalVendorRisk - third-party market and financial intelligence.
# V0004/V0005 are on the ProcureIQ watchlist but not in any Dataverse launch.
# ---------------------------------------------------------------------------
EXTERNAL_VENDOR_RISK_HEADER = "accountnum,vendor_name,credit_rating,financial_health_score,market_risk_tier,diversity_certified,risk_source"
EXTERNAL_VENDOR_RISK_ROWS = [
    "V0001,Contoso Supply Co,C,38.0,High,false,ProcureIQ",
    "V0002,Fabrikam Media,A,82.0,Low,true,ProcureIQ",
    "V0003,SwiftLogix Freight Co.,B+,65.0,Medium,false,ProcureIQ",
    "V0004,Pacific Rim Components Ltd.,B,71.0,Medium,true,ProcureIQ",
    "V0005,Nexus Cloud Services Inc.,C-,29.0,Critical,false,ProcureIQ",
]

# Per-column casts so the Delta table lands with real numeric/boolean types
# (not everything-as-string), which the Direct Lake model and Spark join rely on.
def _as_bool(v: str) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")

VENDOR_ENRICHMENT_TYPES = {
    "accountnum": str, "vendor_name": str, "category": str,
    "on_time_pct": float, "open_disputes": int, "risk_tier": str,
}
EXTERNAL_VENDOR_RISK_TYPES = {
    "accountnum": str, "vendor_name": str, "credit_rating": str,
    "financial_health_score": float, "market_risk_tier": str,
    "diversity_certified": _as_bool, "risk_source": str,
}

TABLES = {
    "VendorEnrichment": {
        "header": VENDOR_ENRICHMENT_HEADER,
        "rows": VENDOR_ENRICHMENT_ROWS,
        "types": VENDOR_ENRICHMENT_TYPES,
    },
    "ExternalVendorRisk": {
        "header": EXTERNAL_VENDOR_RISK_HEADER,
        "rows": EXTERNAL_VENDOR_RISK_ROWS,
        "types": EXTERNAL_VENDOR_RISK_TYPES,
    },
}


def _build_dataframe(tbl: dict):
    """Parse header + CSV rows into a typed pandas DataFrame."""
    import pandas as pd

    cols = tbl["header"].split(",")
    types = tbl["types"]
    records = []
    for row in tbl["rows"]:
        values = row.split(",")
        rec = {}
        for col, raw in zip(cols, values):
            cast = types.get(col, str)
            rec[col] = cast(raw)
        records.append(rec)
    df = pd.DataFrame.from_records(records, columns=cols)
    for col, cast in types.items():
        if cast is int:
            df[col] = df[col].astype("int64")
        elif cast is float:
            df[col] = df[col].astype("float64")
        elif cast is _as_bool:
            df[col] = df[col].astype("bool")
        else:
            df[col] = df[col].astype("string")
    return df


def _write_delta(table_name: str, tbl: dict, storage_token: str, dry_run: bool) -> bool:
    """Write a managed Delta table directly to OneLake Tables/<name> (no Spark).

    Uses the deltalake writer against the OneLake ADLS Gen2 endpoint, so it is
    not subject to the Fabric Spark compute rate limit that the REST table-load
    API hits under capacity contention.
    """
    df = _build_dataframe(tbl)
    if dry_run:
        print(f"  [DRY RUN] write Delta table Tables/{table_name} ({len(df)} rows, "
              f"cols={list(df.columns)})")
        return True
    try:
        from deltalake import write_deltalake

        table_uri = (
            f"abfss://{WS_NAME}@{ONELAKE_HOST}/"
            f"{LH_NAME}.Lakehouse/Tables/{table_name}"
        )
        storage_options = {
            "bearer_token": storage_token,
            "use_fabric_endpoint": "true",
        }
        write_deltalake(
            table_uri, df, mode="overwrite",
            schema_mode="overwrite", storage_options=storage_options,
        )
        print(f"  [OK] wrote Delta table Tables/{table_name} ({len(df)} rows)")
        return True
    except Exception as e:
        print(f"  [ERR] write Delta {table_name}: {e}")
        return False


def _get_fabric_token() -> str:
    from azure.identity import AzureCliCredential
    return AzureCliCredential().get_token("https://api.fabric.microsoft.com/.default").token


def _get_storage_token() -> str:
    from azure.identity import AzureCliCredential
    return AzureCliCredential().get_token("https://storage.azure.com/.default").token


def cmd_apply(dry_run: bool) -> int:
    if not dry_run and not all([WS_NAME, WS_ID, LH_NAME, LH_ID]):
        print("ERROR: Set FABRIC_WORKSPACE_NAME, FABRIC_WORKSPACE_ID, FABRIC_LAKEHOUSE_NAME, FABRIC_LAKEHOUSE_ID in .env")
        return 1

    storage_token = "" if dry_run else _get_storage_token()

    ok = True
    for table_name, tbl in TABLES.items():
        print(f"\n=== {table_name} ===")
        print(f"  Rows: {len(tbl['rows'])}")
        ok &= _write_delta(table_name, tbl, storage_token, dry_run)

    if not dry_run and ok:
        print("\nTables written to OneLake. Allow 1-2 minutes for the Lakehouse SQL")
        print("endpoint to reflect them, then run --verify or refresh the Lakehouse.")

    return 0 if ok else 1


def cmd_verify() -> int:
    """List tables visible in the Lakehouse via Fabric REST API."""
    tok = _get_fabric_token()
    url = f"{FABRIC_API}/workspaces/{WS_ID}/lakehouses/{LH_ID}/tables"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        tables = data.get("data", [])
        our_tables = [t for t in tables if t.get("name") in ("VendorEnrichment", "ExternalVendorRisk")]
        lc_tables = [t for t in tables if t.get("name", "").startswith("lc_")]
        print(f"Lakehouse {LH_ID}: {len(tables)} tables total")
        print(f"\nlc_* tables (Fabric Link): {[t['name'] for t in lc_tables]}")
        print(f"\nSupplementary tables:")
        for t in our_tables:
            print(f"  [{t.get('type')}] {t.get('name')} ✓")
        missing = [n for n in ("VendorEnrichment", "ExternalVendorRisk")
                   if not any(t.get("name") == n for t in tables)]
        if missing:
            print(f"\nMissing: {missing} - run --apply or wait 1-2 min and retry")
        else:
            print("\nAll supplementary tables present and registered.")
    except Exception as e:
        print(f"Verify error: {e}")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Lakehouse supplementary tables for Episode 10.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    load_env("ep-10-dataverse-fabriciq")
    global WS_NAME, WS_ID, LH_NAME, LH_ID
    WS_NAME = os.environ.get("FABRIC_WORKSPACE_NAME", "LaunchControl")
    WS_ID   = os.environ.get("FABRIC_WORKSPACE_ID", "")
    LH_NAME = os.environ.get("FABRIC_LAKEHOUSE_NAME", "")
    LH_ID   = os.environ.get("FABRIC_LAKEHOUSE_ID", "")

    print(f"Workspace : {WS_NAME}")
    print(f"Lakehouse : {LH_NAME or '(dry-run placeholder)'}")

    if args.verify:
        return cmd_verify()
    if args.dry_run or args.apply:
        print(f"Mode      : {'DRY RUN' if args.dry_run else 'APPLY'}")
        return cmd_apply(dry_run=args.dry_run)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
