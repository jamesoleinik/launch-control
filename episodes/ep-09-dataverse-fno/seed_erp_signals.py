"""Episode 9 ERP-signal stand-in: table + seed for eppcdemo1fno.

Why this exists: the F&O (ERP) side of the Ep 9 environment ships as a bare
shell (only the empty `dat` template company), and scripted F&O OData writes
fail in the X++ deserializer, so the live `mserp_` virtual entities are empty.
To make the CRM + ERP "better together" headline result demonstrable today, this
script lands a small, clearly labeled ERP-signal representation in the SAME
Dataverse environment, co-resident with the `lc_` launch tables.

It is a temporary stand-in. Once the F&O environment is provisioned WITH demo
data, swap the agent over to the live F&O virtual entities (mserp_*) / the
Dynamics 365 ERP MCP and retire `lc_erpsignal`.

Idempotent: creating an existing table is skipped; seed rows are upserted by a
natural key (lc_signalkey).

Run:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/seed_erp_signals.py
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
SOLUTION = "LaunchControl"
TABLE = "lc_ERPSignal"
ENTITYSET = "lc_erpsignals"
LAUNCH_CODE = "WIDGET-Q3"

COLUMNS = {
    "lc_SignalKey": "string",
    "lc_LaunchCode": "string",
    "lc_SignalType": "string",
    "lc_Severity": "string",
    "lc_Status": "string",
    "lc_Amount": "decimal",
    "lc_Detail": "memo",
    "lc_Source": "string",
}

# Each row is one ERP signal the agent reads alongside the lc_ launch data.
ROWS = [
    {
        "lc_name": "Budget overrun: Q3 Widget Launch",
        "lc_signalkey": "WIDGET-Q3-BUDGET",
        "lc_launchcode": LAUNCH_CODE,
        "lc_signaltype": "Budget",
        "lc_severity": "Critical",
        "lc_status": "Over budget",
        "lc_amount": 575000,
        "lc_detail": (
            "Approved launch budget 500,000 USD; actual committed spend "
            "575,000 USD (15 percent over). Driven by expedited CDN hardware "
            "and translation vendor overruns."
        ),
        "lc_source": "F&O General ledger (stand-in)",
    },
    {
        "lc_name": "Open vendor PO: CDN edge appliance",
        "lc_signalkey": "WIDGET-Q3-PO-10042",
        "lc_launchcode": LAUNCH_CODE,
        "lc_signaltype": "PurchaseOrder",
        "lc_severity": "Warning",
        "lc_status": "Open (not received)",
        "lc_amount": 82000,
        "lc_detail": (
            "PO-10042 to Northwind CDN Appliances for the CDN edge appliance "
            "required by the launch infrastructure milestone. Status Open, not "
            "yet received; lead time 3 weeks puts it past the launch date."
        ),
        "lc_source": "F&O Procurement (stand-in)",
    },
    {
        "lc_name": "Inventory shortfall: WIDGET-V1",
        "lc_signalkey": "WIDGET-Q3-INV-WIDGETV1",
        "lc_launchcode": LAUNCH_CODE,
        "lc_signaltype": "Inventory",
        "lc_severity": "Critical",
        "lc_status": "Short",
        "lc_amount": 120,
        "lc_detail": (
            "On-hand 120 units of SKU WIDGET-V1 at the Main warehouse against "
            "a launch-day requirement of 500. Shortfall of 380 units with no "
            "open replenishment order."
        ),
        "lc_source": "F&O Inventory management (stand-in)",
    },
]


def ensure_table(client):
    try:
        info = client.tables.describe(TABLE)
        print(f"[skip] table {TABLE} already exists ({info['logical_name']}).")
        return
    except Exception:
        pass
    print(f"[create] {TABLE} in solution {SOLUTION} ...")
    result = client.tables.create(
        TABLE,
        COLUMNS,
        solution=SOLUTION,
        primary_column="lc_Name",
        display_name="ERP Signal (stand-in)",
    )
    print(f"[ok] created {result['logical_name']} "
          f"(entity set {result['entity_set_name']}, "
          f"{result['columns_created']} columns).")


def upsert_rows(url, token):
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    base = f"{url}/api/data/v9.2/{ENTITYSET}"
    for row in ROWS:
        key = row["lc_signalkey"]
        q = (f"{base}?$select=lc_erpsignalid&"
             f"$filter=lc_signalkey eq '{key}'")
        existing = requests.get(q, headers=h).json().get("value", [])
        if existing:
            rid = existing[0]["lc_erpsignalid"]
            requests.patch(f"{base}({rid})", headers=h, json=row).raise_for_status()
            print(f"[update] {key}")
        else:
            requests.post(base, headers=h, json=row).raise_for_status()
            print(f"[insert] {key}")


def main():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)
    client = DataverseClient(url, auth.get_credential())
    print(f"Target env: {url}")
    ensure_table(client)
    upsert_rows(url, token)
    # Summary
    h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(
        f"{url}/api/data/v9.2/{ENTITYSET}?"
        f"$select=lc_signaltype,lc_severity,lc_status,lc_amount&"
        f"$filter=lc_launchcode eq '{LAUNCH_CODE}'",
        headers=h,
    )
    rows = r.json().get("value", [])
    print(f"\nERP signals for {LAUNCH_CODE}: {len(rows)}")
    for s in rows:
        print(f"  - {s['lc_signaltype']:14} {s['lc_severity']:9} "
              f"{s['lc_status']:20} amount={s['lc_amount']}")


if __name__ == "__main__":
    main()
