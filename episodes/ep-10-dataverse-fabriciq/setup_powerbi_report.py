"""
setup_powerbi_report.py  --  Ep 10 Power BI + Fabric IQ consumption layer (Plane 2).

The Power BI Direct Lake semantic model and report must be built in the Fabric
portal / Power BI, but the semantic layer they sit on (the SQL views) can be
applied from here. This script:
  1. Prints the report + Fabric IQ build steps (--instructions).
  2. Prints the semantic-layer SQL (--print-views).
  3. Applies semantic_views.sql to the Lakehouse SQL analytics endpoint
     (--apply-views), idempotent (every view is CREATE OR ALTER).
  4. Lists the Power BI semantic models / reports in the workspace (--verify).

This path needs NO Fabric Data Agent (which is capacity-gated). Power BI Direct
Lake and the Fabric IQ Copilot plugin both run on trial capacity.

Usage:
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --instructions
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --print-views
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views --dry-run
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views
    python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --verify

Prerequisites for --apply-views:
    pip install pyodbc azure-identity   (plus the ODBC Driver 18 for SQL Server)
    If pyodbc is unavailable, paste semantic_views.sql into the Fabric SQL query
    editor over the LaunchControl Lakehouse SQL endpoint instead.

Auth:
    Uses AzureCliCredential (az login).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import load_env  # noqa: E402

FABRIC_API = "https://api.fabric.microsoft.com/v1"
VIEWS_FILE = Path(__file__).with_name("semantic_views.sql")
SPEC_FILE = Path(__file__).with_name("powerbi_report_spec.md")


def _fabric_token() -> str:
    from azure.identity import AzureCliCredential
    return AzureCliCredential().get_token("https://api.fabric.microsoft.com/.default").token


def _sql_token() -> bytes:
    """AAD access token packed for the ODBC SQL_COPT_SS_ACCESS_TOKEN attribute."""
    from azure.identity import AzureCliCredential
    raw = AzureCliCredential().get_token("https://database.windows.net/.default").token
    enc = raw.encode("utf-16-le")
    return struct.pack("<i", len(enc)) + enc


def _api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{FABRIC_API}{path}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _resolve_sql_endpoint(token: str) -> str:
    """Return the Lakehouse SQL analytics endpoint connection string (server)."""
    ws_id, lh_id = os.environ["FABRIC_WORKSPACE_ID"], os.environ["FABRIC_LAKEHOUSE_ID"]
    lh = _api_get(f"/workspaces/{ws_id}/lakehouses/{lh_id}", token)
    props = lh.get("properties", {}).get("sqlEndpointProperties", {})
    server = props.get("connectionString")
    if not server:
        raise RuntimeError(
            "SQL endpoint not provisioned yet for this Lakehouse. Open the "
            "Lakehouse in Fabric once to provision the SQL analytics endpoint."
        )
    return server


def _split_batches(sql_text: str) -> list[str]:
    batches, current = [], []
    for line in sql_text.splitlines():
        if line.strip().upper() == "GO":
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
        else:
            current.append(line)
    tail = "\n".join(current).strip()
    if tail:
        batches.append(tail)
    # Keep only executable batches (skip the comment-only header block).
    return [b for b in batches if re.search(r"CREATE OR ALTER", b, re.IGNORECASE)]


def cmd_print_views() -> int:
    print(VIEWS_FILE.read_text(encoding="utf-8"))
    return 0


def cmd_instructions() -> int:
    print(SPEC_FILE.read_text(encoding="utf-8"))
    return 0


def cmd_apply_views(dry_run: bool) -> int:
    load_env()
    batches = _split_batches(VIEWS_FILE.read_text(encoding="utf-8"))
    view_names = re.findall(r"CREATE OR ALTER VIEW\s+(\w+)",
                            VIEWS_FILE.read_text(encoding="utf-8"), re.IGNORECASE)
    print(f"Semantic views to apply ({len(view_names)}): {', '.join(view_names)}")
    if dry_run:
        for i, b in enumerate(batches, 1):
            print(f"\n--- batch {i} ---\n{b[:200]}{'...' if len(b) > 200 else ''}")
        print("\n[DRY RUN] no statements executed.")
        return 0
    try:
        import pyodbc
    except ImportError:
        print("[ERR] pyodbc not installed. Paste semantic_views.sql into the "
              "Fabric SQL query editor instead, or `pip install pyodbc`.")
        return 2

    server = _resolve_sql_endpoint(_fabric_token())
    database = os.environ.get("FABRIC_LAKEHOUSE_NAME", "")
    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={server};Database={database};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    print(f"Connecting to SQL endpoint: {server} / {database}")
    conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: _sql_token()})
    cur = conn.cursor()
    for i, batch in enumerate(batches, 1):
        try:
            cur.execute(batch)
            conn.commit()
            print(f"  [OK] batch {i}/{len(batches)} applied")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR] batch {i}: {e}")
            return 1
    print("All semantic views applied.")
    return 0


def cmd_verify() -> int:
    load_env()
    token = _fabric_token()
    ws_id = os.environ["FABRIC_WORKSPACE_ID"]
    for kind, path in (("Semantic models", "semanticModels"), ("Reports", "reports")):
        try:
            items = _api_get(f"/workspaces/{ws_id}/{path}", token).get("value", [])
            print(f"\n{kind} in workspace ({len(items)}):")
            for it in items:
                print(f"  - {it.get('displayName')}  [{it.get('id')}]")
        except Exception as e:  # noqa: BLE001
            print(f"  [ERR] listing {kind}: {e}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instructions", action="store_true", help="Print report + Fabric IQ build steps.")
    ap.add_argument("--print-views", action="store_true", help="Print semantic_views.sql.")
    ap.add_argument("--apply-views", action="store_true", help="Apply semantic views to the SQL endpoint.")
    ap.add_argument("--verify", action="store_true", help="List Power BI semantic models / reports.")
    ap.add_argument("--dry-run", action="store_true", help="Preview only (with --apply-views).")
    args = ap.parse_args()

    if args.print_views:
        return cmd_print_views()
    if args.apply_views:
        return cmd_apply_views(args.dry_run)
    if args.verify:
        return cmd_verify()
    return cmd_instructions()


if __name__ == "__main__":
    raise SystemExit(main())
