"""Write demo: outsource a new WIDGET-Q3 task and pay it through Finance & Operations.

This is the **write** half of the Episode 9 "better together" demo. It shows the
two write paths in the unified model and proves the result reads back through the
single Dataverse MCP endpoint:

1. **Write to F&O (the ERP side).** Create a new purchase order in Finance &
   Operations. F&O has no standalone HTTP MCP endpoint, and a create through the
   Dataverse MCP virtual-entity path is rejected by the platform ("Custom plugin
   execution is not allowed in nested pipeline for Virtual Entity"). So the ERP
   write goes through the F&O OData API. This is exactly the operation the
   **Dynamics 365 ERP MCP** tool performs for an agent (in Copilot Studio, or via
   ``dataverse mcp <fno-operations-url>``); see ``erp_mcp_write.py`` for the
   MCP-transport driver and ``MCP-DEMO.md`` for the wiring.

2. **Write to Dataverse through the MCP server (the launch side).** Create the
   matching ``lc_vendorwork`` engagement row through the Dataverse MCP
   ``create_record`` tool, linked to a real WIDGET-Q3 task. This is a genuine
   agent write over the MCP transport (custom tables are not virtual, so the
   nested-pipeline restriction does not apply).

3. **Read it back through the unified MCP.** Query the new PO from the ``mserp_``
   F&O virtual entity and the new engagement from ``lc_vendorwork`` with the
   Dataverse MCP ``read_query`` tool, closing the write -> read loop across both
   planes from one endpoint.

Run (create):
    $env:PYTHONIOENCODING="utf-8"
    python episodes/ep-09-dataverse-fno/write_fno.py

Run (undo, so the demo can be replayed):
    python episodes/ep-09-dataverse-fno/write_fno.py --cleanup

Idempotent: creating twice is a no-op; cleanup removes the Dataverse engagement
and attempts to delete the F&O PO.
"""

import argparse
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth  # noqa: E402
import requests  # noqa: E402
from mcp_client import DataverseMcp, McpError  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
DATA_AREA = "dat"
LAUNCH_CODE = "WIDGET-Q3"

# The new engagement this demo creates.
WORK_KEY = "WIDGET-Q3-VENDORWORK-BETA"
PO_NUMBER = "PO-10507"
VENDOR_ACCT = "V0002"
VENDOR_NAME = "Fabrikam Media"

PURCHASE_ORDER = {
    "dataAreaId": DATA_AREA,
    "PurchaseOrderNumber": PO_NUMBER,
    "OrderVendorAccountNumber": VENDOR_ACCT,
    "CurrencyCode": "USD",
    "LanguageId": "en-us",
    "RequestedDeliveryDate": "2026-09-05T00:00:00Z",
    "PurchaseOrderName": "WIDGET-Q3 beta program landing microsite (Fabrikam)",
}

ENGAGEMENT = {
    "lc_name": "Beta program landing microsite (Fabrikam)",
    "lc_workkey": WORK_KEY,
    "lc_launchcode": LAUNCH_CODE,
    "lc_tasktitle": "Beta program microsite",
    "lc_vendoraccount": VENDOR_ACCT,
    "lc_vendorname": VENDOR_NAME,
    "lc_scope": (
        "Design and build the beta program landing microsite with sign-up flow "
        "and telemetry. Fixed-bid engagement, created live in the demo."
    ),
    "lc_ponumber": PO_NUMBER,
    "lc_committedamount": 26000,
    "lc_invoicedamount": 0,
    "lc_status": "PO open (not received)",
    "lc_duedate": "2026-09-05T00:00:00Z",
}


# ---------------------------------------------------------------------------
# F&O side (OData, the write the ERP MCP wraps) with a retry loop for SSL flaps
# ---------------------------------------------------------------------------

def _fno_call(session, fno_url, method, path, **kw):
    last = None
    for _ in range(5):
        try:
            return session.request(method, f"{fno_url}/data/{path}", timeout=90, **kw)
        except requests.exceptions.RequestException as exc:
            last = exc
            time.sleep(3)
    raise RuntimeError(f"F&O call failed after retries: {last}")


def fno_session(fno_token):
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {fno_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return s


def write_fno_po(session, fno_url):
    key = f"dataAreaId eq '{DATA_AREA}' and PurchaseOrderNumber eq '{PO_NUMBER}'"
    r = _fno_call(session, fno_url, "GET",
                  f"PurchaseOrderHeadersV2?$filter={key}&$top=1")
    if r.status_code == 200 and r.json().get("value"):
        print(f"[skip] F&O PO {PO_NUMBER} already exists")
        return True
    r = _fno_call(session, fno_url, "POST", "PurchaseOrderHeadersV2",
                  json=PURCHASE_ORDER)
    if r.status_code in (200, 201):
        print(f"[ok]   F&O PO {PO_NUMBER} created for vendor {VENDOR_ACCT}")
        return True
    print(f"[FAIL] F&O PO {PO_NUMBER} -> {r.status_code}: {r.text[:200]}")
    return False


def delete_fno_po(session, fno_url):
    r = _fno_call(
        session, fno_url, "DELETE",
        f"PurchaseOrderHeadersV2(dataAreaId='{DATA_AREA}',"
        f"PurchaseOrderNumber='{PO_NUMBER}')")
    if r.status_code in (200, 204):
        print(f"[ok]   F&O PO {PO_NUMBER} deleted")
    else:
        print(f"[warn] F&O PO {PO_NUMBER} delete -> {r.status_code}: {r.text[:160]}")


# ---------------------------------------------------------------------------
# Dataverse side, through the MCP server
# ---------------------------------------------------------------------------

def find_task_id(mcp):
    rows = mcp.read_query(
        "SELECT TOP 1 t.lc_taskid, t.lc_title FROM lc_task t "
        "JOIN lc_launch l ON t.lc_launchid = l.lc_launchid "
        f"WHERE l.lc_code = '{LAUNCH_CODE}' ORDER BY t.lc_title"
    )
    return (rows[0]["lc_taskid"], rows[0].get("lc_title")) if rows else (None, None)


def engagement_id(mcp):
    rows = mcp.read_query(
        "SELECT lc_vendorworkid FROM lc_vendorwork "
        f"WHERE lc_workkey = '{WORK_KEY}'"
    )
    return rows[0]["lc_vendorworkid"] if rows else None


def write_engagement_via_mcp(mcp):
    if engagement_id(mcp):
        print(f"[skip] engagement {WORK_KEY} already exists")
        return True
    item = dict(ENGAGEMENT)
    task_id, task_title = find_task_id(mcp)
    if task_id:
        item["lc_taskid"] = {"relatedTable": "lc_task", "recordId": task_id}
        print(f"[bind] linking engagement to task '{task_title}'")
    else:
        print("[warn] no WIDGET-Q3 task found; creating engagement unlinked")
    mcp.create_record("lc_vendorwork", item)
    print(f"[ok]   Dataverse engagement {WORK_KEY} created via MCP create_record")
    return True


def delete_engagement_via_mcp(mcp):
    rid = engagement_id(mcp)
    if not rid:
        print(f"[skip] engagement {WORK_KEY} not present")
        return
    mcp.call("delete_record",
             {"tablename": "lc_vendorwork", "hasUserApproved": True, "recordId": rid})
    print(f"[ok]   Dataverse engagement {WORK_KEY} deleted via MCP delete_record")


# ---------------------------------------------------------------------------
# Unified read-back through the Dataverse MCP
# ---------------------------------------------------------------------------

def read_back(mcp):
    print("\n== unified read-back through the Dataverse MCP ==\n")

    po_rows = mcp.read_query(
        "SELECT mserp_purchaseordernumber, mserp_ordervendoraccountnumber, "
        "mserp_purchaseordername FROM mserp_purchpurchaseorderheaderv2entity "
        f"WHERE mserp_purchaseordernumber = '{PO_NUMBER}'"
    )
    po_ok = bool(po_rows)
    if po_ok:
        p = po_rows[0]
        print(f"  [F&O PO ] {p['mserp_purchaseordernumber']} "
              f"vendor={p['mserp_ordervendoraccountnumber']} "
              f"\"{p.get('mserp_purchaseordername', '')}\"")
    else:
        print(f"  [F&O PO ] {PO_NUMBER} not visible through mserp_ virtual entity")

    eng_rows = mcp.read_query(
        "SELECT lc_workkey, lc_vendorname, lc_ponumber, lc_committedamount, "
        f"lc_status FROM lc_vendorwork WHERE lc_workkey = '{WORK_KEY}'"
    )
    eng_ok = bool(eng_rows)
    if eng_ok:
        e = eng_rows[0]
        print(f"  [engage ] {e['lc_workkey']} -> {e['lc_vendorname']} "
              f"{e['lc_ponumber']} committed={float(e.get('lc_committedamount') or 0):.0f} "
              f"({e.get('lc_status')})")
    else:
        print(f"  [engage ] {WORK_KEY} not found in lc_vendorwork")

    return po_ok, eng_ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup", action="store_true",
                        help="remove the demo engagement and F&O PO, then exit")
    args = parser.parse_args()

    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    fno_url = os.environ["FNO_URL"].rstrip("/")
    dv_token = auth.get_token(EPISODE)
    fno_token = auth.get_credential(EPISODE).get_token(f"{fno_url}/.default").token

    mcp = DataverseMcp(url, dv_token)
    info = mcp.initialize(client_name="write_fno")
    print(f"Dataverse MCP: {info.get('name')} v{info.get('version')} at {url}/api/mcp")
    print(f"F&O OData    : {fno_url}/data\n")

    session = fno_session(fno_token)

    if args.cleanup:
        print("== cleanup ==")
        delete_engagement_via_mcp(mcp)
        delete_fno_po(session, fno_url)
        return

    print("== 1. write to F&O (the write the Dynamics 365 ERP MCP wraps) ==")
    fno_ok = write_fno_po(session, fno_url)

    print("\n== 2. write to Dataverse through the MCP server ==")
    try:
        eng_written = write_engagement_via_mcp(mcp)
    except McpError as exc:
        print(f"[FAIL] MCP create_record: {exc}")
        eng_written = False

    po_ok, eng_ok = read_back(mcp)

    print("\n== Result ==")
    print(f"  F&O PO write (OData / ERP MCP path) : {'PASS' if fno_ok else 'FAIL'}")
    print(f"  Dataverse engagement write via MCP  : {'PASS' if eng_written else 'FAIL'}")
    print(f"  PO reads back via unified MCP        : {'PASS' if po_ok else 'FAIL'}")
    print(f"  Engagement reads back via unified MCP: {'PASS' if eng_ok else 'FAIL'}")

    if not (fno_ok and eng_written and po_ok and eng_ok):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
