"""Episode 9 CRM + ERP join: outsourced launch work paid through F&O.

This is the concrete "better together" payload. Dataverse owns the launch plan
(``lc_launch`` / ``lc_task``) and the decision to outsource a task. Dynamics 365
Finance and Operations (F&O) owns the vendor master and the purchase order. This
script wires the two together so an agent can reason across both from one env:

  launch task  ->  lc_vendorwork  ->  real F&O vendor + open PO

What it does (idempotent, safe to re-run):

1. F&O side (direct OData writes, the reliable loader on a bare env):
   - Ensures currency USD and vendor group ``DEMO`` exist.
   - Ensures vendor ``V0001`` (Contoso Supply Co) exists.
   - Ensures one open purchase order header per outsourced engagement. Lines are
     omitted on purpose: this bare env has no released products or procurement
     categories, so an open PO header is the deepest real document available
     without a posting/config project. The committed and invoiced amounts are
     carried on ``lc_vendorwork``.

2. Dataverse side:
   - Ensures the ``lc_vendorwork`` table (a first-class launch <-> procurement
     join) with a real ``lc_taskid`` lookup to ``lc_task``, plus the F&O business
     keys (``lc_vendoraccount`` / ``lc_ponumber``) so the row validates and joins
     against live F&O whether or not the ``mserp_`` virtual entities are enabled.
   - Marks the outsourced tasks and upserts one ``lc_vendorwork`` row each,
     pointing at the real F&O vendor and PO.
   - Pins two demo task statuses the assistive reconciliation agent reads: the
     translation task stays Blocked (the discrepancy it holds) and the hero-copy
     task stays InProgress so the agent marks it complete live before posting
     (the clean pass PO-10514).

Why business keys instead of a Dataverse lookup to a virtual entity: the Finance
and Operations virtual entities (``mserp_*``) are generated per entity (a one-time
"Visible" toggle on the "Available finance and operations entities" catalog, see
the README). Storing the F&O keys keeps the join durable regardless of whether the
``mserp_`` tables are enabled, and it is the only key that also works over the
Dataverse SQL (TDS) endpoint, which does not expose virtual entities. Once the
``mserp_`` tables are generated, the same keys light up a live OData join with no
reseed:

  lc_vendorwork.lc_vendoraccount -> mserp_vendvendorv2entities.mserp_vendoraccountnumber
  lc_vendorwork.lc_ponumber      -> mserp_purchpurchaseorderheaderv2entities.mserp_purchaseordernumber

3. Additive virtual-table lookups (add_vendorwork_lookups): once the ``mserp_``
   tables are generated, this also creates two real N:1 lookups from
   ``lc_vendorwork`` (a standard table) to the F&O virtual tables and binds the
   seeded rows, so a model-driven app shows related F&O detail:

  lc_vendorwork.lc_VendorRef -> mserp_vendvendorv2entity            (by VendorAccountNumber)
  lc_vendorwork.lc_PORef     -> mserp_purchpurchaseorderheaderv2entity (by PurchaseOrderNumber)

   The lookups are additive: the plain-text keys remain the durable join (and the
   only one that works over SQL / TDS). Standard -> virtual is the supported lookup
   direction; cascades are None.

Run:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/scripts/seed_vendor_work.py
"""

import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402
import add_vendorwork_lookups  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
SOLUTION = "LaunchControl"
DATA_AREA = "dat"
LAUNCH_CODE = "WIDGET-Q3"

TABLE = "lc_VendorWork"
ENTITYSET = "lc_vendorworks"

# Simple columns only (string / decimal / memo / datetime). The lc_taskid lookup
# is added separately after the table exists.
COLUMNS = {
    "lc_WorkKey": "string",
    "lc_LaunchCode": "string",
    "lc_TaskTitle": "string",
    "lc_VendorAccount": "string",
    "lc_VendorName": "string",
    "lc_Scope": "memo",
    "lc_PONumber": "string",
    "lc_CommittedAmount": "decimal",
    "lc_InvoicedAmount": "decimal",
    "lc_Status": "string",
    "lc_DueDate": "datetime",
}

# Currency + vendor master the engagements depend on.
CURRENCY = {"CurrencyCode": "USD", "CurrencyCodeISO": "USD", "Name": "US Dollar"}
VENDOR_GROUP = {"dataAreaId": DATA_AREA, "VendorGroupId": "DEMO",
                "Description": "Demo vendors"}
VENDORS = [
    {
        "dataAreaId": DATA_AREA,
        "VendorAccountNumber": "V0001",
        "VendorName": "Contoso Supply Co",
        "VendorGroupId": "DEMO",
        "VendorPartyType": "Organization",
        "CurrencyCode": "USD",
    },
    {
        "dataAreaId": DATA_AREA,
        "VendorAccountNumber": "V0002",
        "VendorName": "Fabrikam Media",
        "VendorGroupId": "DEMO",
        "VendorPartyType": "Organization",
        "CurrencyCode": "USD",
    },
    {
        "dataAreaId": DATA_AREA,
        "VendorAccountNumber": "V0003",
        "VendorName": "Northwind Legal Advisors",
        "VendorGroupId": "DEMO",
        "VendorPartyType": "Organization",
        "CurrencyCode": "USD",
    },
]

# One open PO header per outsourced engagement.
PURCHASE_ORDERS = [
    {
        "dataAreaId": DATA_AREA,
        "PurchaseOrderNumber": "PO-10501",
        "OrderVendorAccountNumber": "V0001",
        "CurrencyCode": "USD",
        "LanguageId": "en-us",
        "RequestedDeliveryDate": "2026-09-15T00:00:00Z",
        "PurchaseOrderName": "WIDGET-Q3 localization outsourcing (Contoso)",
    },
    {
        "dataAreaId": DATA_AREA,
        "PurchaseOrderNumber": "PO-10502",
        "OrderVendorAccountNumber": "V0001",
        "CurrencyCode": "USD",
        "LanguageId": "en-us",
        "RequestedDeliveryDate": "2026-08-20T00:00:00Z",
        "PurchaseOrderName": "WIDGET-Q3 launch video outsourcing (Contoso)",
    },
    {
        "dataAreaId": DATA_AREA,
        "PurchaseOrderNumber": "PO-10503",
        "OrderVendorAccountNumber": "V0001",
        "CurrencyCode": "USD",
        "LanguageId": "en-us",
        "RequestedDeliveryDate": "2026-08-05T00:00:00Z",
        "PurchaseOrderName": "WIDGET-Q3 load testing outsourcing (Contoso)",
    },
    {
        "dataAreaId": DATA_AREA,
        "PurchaseOrderNumber": "PO-10514",
        "OrderVendorAccountNumber": "V0002",
        "CurrencyCode": "USD",
        "LanguageId": "en-us",
        "RequestedDeliveryDate": "2026-08-12T00:00:00Z",
        "PurchaseOrderName": "WIDGET-Q3 hero copy + visuals (Fabrikam)",
    },
    {
        "dataAreaId": DATA_AREA,
        "PurchaseOrderNumber": "PO-10505",
        "OrderVendorAccountNumber": "V0002",
        "CurrencyCode": "USD",
        "LanguageId": "en-us",
        "RequestedDeliveryDate": "2026-08-28T00:00:00Z",
        "PurchaseOrderName": "WIDGET-Q3 quickstart tutorial (Fabrikam)",
    },
    {
        "dataAreaId": DATA_AREA,
        "PurchaseOrderNumber": "PO-10506",
        "OrderVendorAccountNumber": "V0003",
        "CurrencyCode": "USD",
        "LanguageId": "en-us",
        "RequestedDeliveryDate": "2026-07-30T00:00:00Z",
        "PurchaseOrderName": "WIDGET-Q3 DPA addendum legal review (Northwind)",
    },
]

# The launch tasks that get outsourced, matched to the real F&O vendor + PO.
ENGAGEMENTS = [
    {
        "lc_name": "Localization: translate docs + UI (Contoso)",
        "lc_workkey": "WIDGET-Q3-VENDORWORK-TRANSLATION",
        "lc_launchcode": LAUNCH_CODE,
        "lc_tasktitle": "Translation vendor contract",
        "lc_vendoraccount": "V0001",
        "lc_vendorname": "Contoso Supply Co",
        "lc_scope": (
            "Translate product docs and UI strings into 6 locales, deliver TMX "
            "back to the localization milestone. Fixed-bid engagement."
        ),
        "lc_ponumber": "PO-10501",
        "lc_committedamount": 45000,
        "lc_invoicedamount": 0,
        "lc_status": "PO open (not received)",
        "lc_duedate": "2026-09-15T00:00:00Z",
    },
    {
        "lc_name": "Launch video production (Contoso)",
        "lc_workkey": "WIDGET-Q3-VENDORWORK-VIDEO",
        "lc_launchcode": LAUNCH_CODE,
        "lc_tasktitle": "Launch video (90s)",
        "lc_vendoraccount": "V0001",
        "lc_vendorname": "Contoso Supply Co",
        "lc_scope": (
            "Produce the 90-second launch hero video: script polish, shoot, "
            "edit, and two revision rounds. Milestone billing."
        ),
        "lc_ponumber": "PO-10502",
        "lc_committedamount": 37000,
        "lc_invoicedamount": 12000,
        "lc_status": "Invoice pending",
        "lc_duedate": "2026-08-20T00:00:00Z",
    },
    {
        "lc_name": "Load + soak testing at 5x peak (Contoso)",
        "lc_workkey": "WIDGET-Q3-VENDORWORK-LOADTEST",
        "lc_launchcode": LAUNCH_CODE,
        "lc_tasktitle": "Load test API at 5x peak",
        "lc_vendoraccount": "V0001",
        "lc_vendorname": "Contoso Supply Co",
        "lc_scope": (
            "Run 5x-peak load and 12-hour soak tests against the API, deliver a "
            "latency/error report and tuning recommendations. Time-and-materials."
        ),
        "lc_ponumber": "PO-10503",
        "lc_committedamount": 28000,
        "lc_invoicedamount": 28000,
        "lc_status": "Invoiced (paid)",
        "lc_duedate": "2026-08-05T00:00:00Z",
    },
    {
        "lc_name": "Hero copy + key visuals (Fabrikam)",
        "lc_workkey": "WIDGET-Q3-VENDORWORK-HEROCOPY",
        "lc_launchcode": LAUNCH_CODE,
        "lc_tasktitle": "Hero copy + visuals",
        "lc_vendoraccount": "V0002",
        "lc_vendorname": "Fabrikam Media",
        "lc_scope": (
            "Write launch hero copy and produce three key visuals for the "
            "landing page and social. Two revision rounds. Fixed-bid."
        ),
        "lc_ponumber": "PO-10514",
        "lc_committedamount": 22000,
        "lc_invoicedamount": 8000,
        "lc_status": "Invoice pending",
        "lc_duedate": "2026-08-12T00:00:00Z",
    },
    {
        "lc_name": "Quickstart tutorial authoring (Fabrikam)",
        "lc_workkey": "WIDGET-Q3-VENDORWORK-QUICKSTART",
        "lc_launchcode": LAUNCH_CODE,
        "lc_tasktitle": "Quickstart tutorial",
        "lc_vendoraccount": "V0002",
        "lc_vendorname": "Fabrikam Media",
        "lc_scope": (
            "Author the end-to-end quickstart tutorial with runnable samples in "
            "three languages. Fixed-bid engagement."
        ),
        "lc_ponumber": "PO-10505",
        "lc_committedamount": 15000,
        "lc_invoicedamount": 0,
        "lc_status": "PO open (not received)",
        "lc_duedate": "2026-08-28T00:00:00Z",
    },
    {
        "lc_name": "DPA addendum legal review (Northwind)",
        "lc_workkey": "WIDGET-Q3-VENDORWORK-DPA",
        "lc_launchcode": LAUNCH_CODE,
        "lc_tasktitle": "DPA addendum review",
        "lc_vendoraccount": "V0003",
        "lc_vendorname": "Northwind Legal Advisors",
        "lc_scope": (
            "Outside-counsel review of the data processing addendum for the "
            "launch, redline and sign-off memo. Fixed-fee."
        ),
        "lc_ponumber": "PO-10506",
        "lc_committedamount": 18000,
        "lc_invoicedamount": 18000,
        "lc_status": "Invoiced (paid)",
        "lc_duedate": "2026-07-30T00:00:00Z",
    },
]


# ---------------------------------------------------------------------------
# F&O side (direct OData with a small retry loop for the flaky endpoint)
# ---------------------------------------------------------------------------

def _fno_session(token):
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return s


def _fno_call(s, fno_url, method, path, **kw):
    last = None
    for _ in range(5):
        try:
            return s.request(method, f"{fno_url}/data/{path}", timeout=90, **kw)
        except requests.exceptions.RequestException as exc:  # SSL/connection flaps
            last = exc
            time.sleep(3)
    raise RuntimeError(f"F&O call failed after retries: {last}")


def _fno_ensure(s, fno_url, entityset, key_filter, body, label):
    r = _fno_call(s, fno_url, "GET", f"{entityset}?$filter={key_filter}&$top=1")
    if r.status_code == 200 and r.json().get("value"):
        print(f"[skip] F&O {label} exists")
        return
    r = _fno_call(s, fno_url, "POST", entityset, json=body)
    if r.status_code in (200, 201):
        print(f"[ok]   F&O {label} created")
    else:
        print(f"[warn] F&O {label} -> {r.status_code}: {r.text[:200]}")


def seed_fno(fno_url, token):
    s = _fno_session(token)
    _fno_ensure(s, fno_url, "Currencies", "CurrencyCode eq 'USD'", CURRENCY,
                "currency USD")
    _fno_ensure(s, fno_url, "VendorGroups",
                f"dataAreaId eq '{DATA_AREA}' and VendorGroupId eq 'DEMO'",
                VENDOR_GROUP, "vendor group DEMO")
    for vendor in VENDORS:
        acct = vendor["VendorAccountNumber"]
        _fno_ensure(
            s, fno_url, "Vendors",
            f"dataAreaId eq '{DATA_AREA}' and VendorAccountNumber eq '{acct}'",
            vendor, f"vendor {acct}")
    for po in PURCHASE_ORDERS:
        num = po["PurchaseOrderNumber"]
        _fno_ensure(
            s, fno_url, "PurchaseOrderHeadersV2",
            f"dataAreaId eq '{DATA_AREA}' and PurchaseOrderNumber eq '{num}'",
            po, f"open PO {num}")


# ---------------------------------------------------------------------------
# Dataverse side
# ---------------------------------------------------------------------------

def ensure_table(client):
    if client.tables.get(TABLE):
        print(f"[skip] table {TABLE} exists")
    else:
        print(f"[create] {TABLE} ...")
        result = client.tables.create(
            TABLE, COLUMNS, solution=SOLUTION,
            primary_column="lc_Name", display_name="Vendor Work",
        )
        print(f"[ok]   created {result['logical_name']} "
              f"(entity set {result['entity_set_name']}, "
              f"{result['columns_created']} columns)")

    cols = client.tables.list_columns("lc_vendorwork") or []
    names = {
        (c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None))
        for c in cols
    }
    if "lc_taskid" in names:
        print("[skip] lookup lc_vendorwork.lc_taskid -> lc_task exists")
        return
    print("[create] lookup lc_vendorwork.lc_taskid -> lc_task ...")
    for attempt in range(8):
        try:
            client.tables.create_lookup_field(
                "lc_vendorwork", "lc_taskid", "lc_task",
                display_name="Outsourced Task", solution=SOLUTION,
            )
            print("[ok]   lookup created")
            return
        except Exception as exc:  # noqa: BLE001 - retry on metadata lock/propagation
            if "duplicate" in str(exc).lower() or "already exists" in str(exc).lower():
                print("[skip] lookup exists (race)")
                return
            wait = min(2 ** attempt, 30)
            print(f"       retry {attempt + 1}/8 in {wait}s ({str(exc)[:80]})")
            time.sleep(wait)
    raise RuntimeError("could not create lc_taskid lookup")


def _task_ids_by_title(url, h):
    r = requests.get(
        f"{url}/api/data/v9.2/lc_tasks?$select=lc_taskid,lc_title", headers=h)
    r.raise_for_status()
    return {t["lc_title"]: t["lc_taskid"] for t in r.json().get("value", [])}


# Deterministic demo task statuses for the assistive reconciliation agent. The
# work-complete check reads lc_task.lc_taskstatus, so the demo pins exactly two
# outcomes: the translation task stays Blocked (the engineered discrepancy the
# agent holds), and the hero-copy task stays InProgress so the agent marks it
# complete live in the clean pass (PO-10514) before posting. lc_taskstatus:
# NotStarted=10600301, InProgress=10600302, Blocked=10600303, Done=10600304.
TASK_STATUS_BY_TITLE = {
    "Translation vendor contract": 10600303,  # Blocked (discrepancy: work not done)
    "Hero copy + visuals": 10600302,          # InProgress (agent marks it Done live)
}


def set_task_statuses(url, token):
    h = {
        "Authorization": f"******",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    task_ids = _task_ids_by_title(url, h)
    for title, status in TASK_STATUS_BY_TITLE.items():
        tid = task_ids.get(title)
        if not tid:
            print(f"[warn] task '{title}' not found; cannot set status")
            continue
        requests.patch(
            f"{url}/api/data/v9.2/lc_tasks({tid})", headers=h,
            json={"lc_taskstatus": status}).raise_for_status()
        label = {10600301: "NotStarted", 10600302: "InProgress",
                 10600303: "Blocked", 10600304: "Done"}.get(status, str(status))
        print(f"[status] task '{title}' -> {label}")


def upsert_engagements(url, token):
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    base = f"{url}/api/data/v9.2/{ENTITYSET}"
    task_ids = _task_ids_by_title(url, h)
    for eng in ENGAGEMENTS:
        row = dict(eng)
        tid = task_ids.get(eng["lc_tasktitle"])
        if tid:
            row["lc_taskid@odata.bind"] = f"/lc_tasks({tid})"
        else:
            print(f"[warn] task '{eng['lc_tasktitle']}' not found; row unlinked")
        key = eng["lc_workkey"]
        q = f"{base}?$select=lc_vendorworkid&$filter=lc_workkey eq '{key}'"
        existing = requests.get(q, headers=h).json().get("value", [])
        if existing:
            rid = existing[0]["lc_vendorworkid"]
            requests.patch(f"{base}({rid})", headers=h, json=row).raise_for_status()
            print(f"[update] {key} -> task '{eng['lc_tasktitle']}'")
        else:
            requests.post(base, headers=h, json=row).raise_for_status()
            print(f"[insert] {key} -> task '{eng['lc_tasktitle']}'")


def summarize(url, token):
    h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    r = requests.get(
        f"{url}/api/data/v9.2/{ENTITYSET}?"
        f"$select=lc_tasktitle,lc_vendorname,lc_ponumber,lc_committedamount,"
        f"lc_invoicedamount,lc_status,lc_duedate&"
        f"$filter=lc_launchcode eq '{LAUNCH_CODE}'", headers=h)
    rows = r.json().get("value", [])
    committed = sum(x.get("lc_committedamount") or 0 for x in rows)
    invoiced = sum(x.get("lc_invoicedamount") or 0 for x in rows)
    print(f"\nOutsourced work for {LAUNCH_CODE}: {len(rows)} engagement(s)")
    for x in rows:
        print(f"  - {x['lc_tasktitle']:26} {x['lc_vendorname']:18} "
              f"{x['lc_ponumber']:9} committed={x['lc_committedamount']:>8} "
              f"invoiced={x['lc_invoicedamount']:>8} {x['lc_status']}")
    print(f"  Total committed={committed}  invoiced={invoiced}  "
          f"open={committed - invoiced}")


def main():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    fno_url = os.environ.get("FNO_URL", "").rstrip("/")
    if not fno_url:
        raise SystemExit(
            "FNO_URL is not set. Add it to the episode .env "
            "(for example https://<your-fno-env>.operations.dynamics.com).")
    dv_token = auth.get_token(EPISODE)
    fno_token = auth.get_credential(EPISODE).get_token(f"{fno_url}/.default").token
    print(f"Dataverse env: {url}")
    print(f"F&O env:       {fno_url}\n")

    print("== F&O: vendor master + open POs ==")
    seed_fno(fno_url, fno_token)

    print("\n== Dataverse: lc_vendorwork table + lookup ==")
    client = DataverseClient(url, auth.get_credential(EPISODE))
    ensure_table(client)

    print("\n== Dataverse: seed the launch <-> procurement join ==")
    upsert_engagements(url, dv_token)

    print("\n== Dataverse: pin demo task statuses (discrepancy + clean pass) ==")
    set_task_statuses(url, dv_token)

    print("\n== Dataverse: F&O virtual-table lookups on lc_vendorwork ==")
    add_vendorwork_lookups.apply_lookups(url, dv_token)

    summarize(url, dv_token)


if __name__ == "__main__":
    main()
