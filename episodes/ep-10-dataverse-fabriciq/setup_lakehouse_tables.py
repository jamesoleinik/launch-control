"""
setup_lakehouse_tables.py  --  Ep 10 Fabric Lakehouse supplementary table setup.

Seeds VendorEnrichment and ExternalVendorRisk as managed Delta tables in the
Fabric Lakehouse. Uploads CSV files to the Lakehouse Files section via OneLake
ADLS Gen2, then calls the Fabric REST API table-load endpoint to register
them as managed Delta tables in the Lakehouse SQL analytics endpoint.

Architecture:
    Dataverse (lc_* tables)  +  F&O (fno_* tables)
           ↓ Fabric Link (low-latency, ~46s median measured)
    Lakehouse (Delta Parquet on OneLake)
           + VendorEnrichment    (seeded by this script)
           + ExternalVendorRisk  (seeded by this script)
           ↓ SQL analytics endpoint
    Fabric Data Agent  →  natural-language queries
           ↓ connected agent
    Launch Analyst (Copilot Studio)  →  Teams alert

Usage:
    # Dry-run (print what would be written):
    python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --dry-run

    # Apply (idempotent: uploads CSVs and registers tables):
    python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --apply

    # Verify tables are visible in Lakehouse SQL endpoint:
    python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --verify

Prerequisites:
    pip install azure-storage-file-datalake azure-identity pandas

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
STAGING_PATH = "Files/supplemental"  # CSV staging area in the Lakehouse Files section

# ---------------------------------------------------------------------------
# VendorEnrichment — internal vendor performance data.
# ---------------------------------------------------------------------------
VENDOR_ENRICHMENT_HEADER = "accountnum,vendor_name,category,on_time_pct,open_disputes,risk_tier"
VENDOR_ENRICHMENT_ROWS = [
    "V0001,Acme Translations Inc.,Localization,0.61,2,High",
    "V0002,GlobalTech Licensing Ltd.,Software Licensing,0.88,0,Low",
    "V0003,SwiftLogix Freight Co.,Logistics,0.74,1,Medium",
]

# ---------------------------------------------------------------------------
# ExternalVendorRisk — third-party market and financial intelligence.
# V0004/V0005 are on the ProcureIQ watchlist but not in any Dataverse launch.
# ---------------------------------------------------------------------------
EXTERNAL_VENDOR_RISK_HEADER = "accountnum,vendor_name,credit_rating,financial_health_score,market_risk_tier,diversity_certified,risk_source"
EXTERNAL_VENDOR_RISK_ROWS = [
    "V0001,Acme Translations Inc.,C,38.0,High,false,ProcureIQ",
    "V0002,GlobalTech Licensing Ltd.,A,82.0,Low,true,ProcureIQ",
    "V0003,SwiftLogix Freight Co.,B+,65.0,Medium,false,ProcureIQ",
    "V0004,Pacific Rim Components Ltd.,B,71.0,Medium,true,ProcureIQ",
    "V0005,Nexus Cloud Services Inc.,C-,29.0,Critical,false,ProcureIQ",
]

TABLES = {
    "VendorEnrichment": {
        "header": VENDOR_ENRICHMENT_HEADER,
        "rows": VENDOR_ENRICHMENT_ROWS,
    },
    "ExternalVendorRisk": {
        "header": EXTERNAL_VENDOR_RISK_HEADER,
        "rows": EXTERNAL_VENDOR_RISK_ROWS,
    },
}


def _get_fabric_token() -> str:
    from azure.identity import AzureCliCredential
    return AzureCliCredential().get_token("https://api.fabric.microsoft.com/.default").token


def _get_storage_token() -> str:
    from azure.identity import AzureCliCredential
    return AzureCliCredential().get_token("https://storage.azure.com/.default").token


def _upload_csv(table_name: str, csv_content: str, storage_token: str, dry_run: bool) -> bool:
    """Upload CSV to Lakehouse Files/supplemental/<table>.csv via ADLS Gen2."""
    if dry_run:
        print(f"  [DRY RUN] upload {STAGING_PATH}/{table_name}.csv ({len(csv_content)} bytes)")
        return True
    try:
        from azure.storage.filedatalake import DataLakeServiceClient
        from azure.core.credentials import AccessToken
        import time as _time

        class _StaticCred:
            def get_token(self, *_scopes, **_kw):
                return AccessToken(storage_token, int(_time.time()) + 3600)

        svc = DataLakeServiceClient(
            account_url=f"https://{ONELAKE_HOST}",
            credential=_StaticCred(),
        )
        fs = svc.get_file_system_client(file_system=WS_NAME)
        path = f"{LH_NAME}.Lakehouse/{STAGING_PATH}/{table_name}.csv"
        fc = fs.get_file_client(path)
        data = csv_content.encode("utf-8")
        fc.upload_data(data, overwrite=True)
        print(f"  [OK] uploaded {STAGING_PATH}/{table_name}.csv")
        return True
    except Exception as e:
        print(f"  [ERR] upload {table_name}: {e}")
        return False


def _load_table(table_name: str, fabric_token: str, dry_run: bool) -> bool:
    """Call Fabric table-load API to create a managed Delta table from the CSV."""
    if dry_run:
        print(f"  [DRY RUN] load table {table_name} from {STAGING_PATH}/{table_name}.csv")
        return True
    url = f"{FABRIC_API}/workspaces/{WS_ID}/lakehouses/{LH_ID}/tables/{table_name}/load"
    body = json.dumps({
        "relativePath": f"{STAGING_PATH}/{table_name}.csv",
        "pathType": "File",
        "mode": "Overwrite",
        "recursive": False,
        "formatOptions": {
            "format": "Csv",
            "header": True,
            "delimiter": ","
        }
    }).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {fabric_token}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status = r.status
            op_location = r.headers.get("Location") or r.headers.get("x-ms-operation-id")
            print(f"  [OK] load {table_name}: HTTP {status} (async)")
            if op_location:
                _poll_load_op(op_location, fabric_token, table_name)
            return True
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:300]
        if "already exists" in msg.lower() or "conflict" in msg.lower():
            print(f"  [SKIP] {table_name} already registered")
            return True
        print(f"  [ERR] load {table_name}: HTTP {e.code} {msg}")
        return False
    except Exception as e:
        print(f"  [ERR] load {table_name}: {e}")
        return False


def _poll_load_op(op_url: str, token: str, table_name: str, max_wait: int = 120) -> None:
    """Poll a Fabric async operation until it completes or times out."""
    # op_url may be just an ID; try constructing the full URL
    if not op_url.startswith("http"):
        op_url = f"{FABRIC_API}/operations/{op_url}"
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(5)
        req = urllib.request.Request(op_url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                op = json.loads(r.read())
            state = op.get("status", op.get("Status", "?"))
            print(f"  [poll] {table_name} load: {state}")
            if state.lower() in ("succeeded", "completed", "done"):
                print(f"  [OK] {table_name} load completed")
                return
            if state.lower() in ("failed", "error"):
                print(f"  [ERR] {table_name} load failed: {op}")
                return
        except Exception as e:
            print(f"  [poll err] {e}")
            break
    print(f"  [WARN] {table_name} load still running after {max_wait}s — check Fabric portal")


def cmd_apply(dry_run: bool) -> int:
    if not dry_run and not all([WS_NAME, WS_ID, LH_NAME, LH_ID]):
        print("ERROR: Set FABRIC_WORKSPACE_NAME, FABRIC_WORKSPACE_ID, FABRIC_LAKEHOUSE_NAME, FABRIC_LAKEHOUSE_ID in .env")
        return 1

    storage_token = "" if dry_run else _get_storage_token()
    fabric_token = "" if dry_run else _get_fabric_token()

    ok = True
    for table_name, tbl in TABLES.items():
        print(f"\n=== {table_name} ===")
        csv_content = tbl["header"] + "\n" + "\n".join(tbl["rows"])
        print(f"  Rows: {len(tbl['rows'])}")

        ok &= _upload_csv(table_name, csv_content, storage_token, dry_run)
        if not dry_run:
            time.sleep(2)  # brief pause before load
        ok &= _load_table(table_name, fabric_token, dry_run)

    if not dry_run and ok:
        print("\nTables registered. Allow 1-2 minutes for the Lakehouse SQL endpoint")
        print("to reflect them, then run --verify or refresh the Lakehouse in Fabric portal.")

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
            print(f"\nMissing: {missing} — run --apply or wait 1-2 min and retry")
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
