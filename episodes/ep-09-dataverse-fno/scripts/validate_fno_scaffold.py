"""Validate the Finance & Operations scaffolding the vendor-invoice scenario needs.

Read-only. Enumerates every F&O object the PO -> product receipt -> vendor invoice
flow depends on, in dependency order, and reports what exists versus what is missing
against the target legal entity. This is the runtime check behind Episode 9 Act 2
(populate the model through the ERP and Dataverse MCP servers): run it before and
after populating to see the live gap.

The scaffold is grouped into three layers:

  Config  company-level financial configuration. On a bare legal entity these are
          absent and can only be stood up through the F&O ERP MCP *form tools*
          (they drive the configuration forms and their X++ logic); raw OData
          cannot create a chart of accounts or wire the ledger. See the number
          sequence preamble in the episode README.
  Master  vendor and product master data plus purchase orders (ERP MCP data tools).
  Txn     product receipts and vendor invoices (blocked until Config exists).

Run:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/scripts/validate_fno_scaffold.py
    python episodes/ep-09-dataverse-fno/scripts/validate_fno_scaffold.py --company USMF

Exit code is 0 when every Txn-enabling Config item is present, 1 otherwise, so it
can gate a build.
"""

import argparse
import os
import sys
import time

import urllib3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EPISODE = "ep-09-dataverse-fno"
DEFAULT_COMPANY = "dat"

# Each row: (layer, label, collection, filter_template, built_by)
# {c} in the filter template is replaced with the company (dataAreaId).
SCAFFOLD = [
    ("Config", "Ledger accounting currency", "Ledgers",
     "LegalEntityId eq '{c}' and AccountingCurrency ne ''", "ERP MCP form tools"),
    ("Config", "Chart of accounts", "ChartOfAccounts", None, "ERP MCP form tools"),
    ("Config", "Main accounts", "MainAccounts", None, "ERP MCP form tools"),
    ("Config", "Fiscal calendars", "FiscalCalendarsEntity", None, "ERP MCP form tools"),
    ("Config", "Account structures", "AccountStructures", None, "ERP MCP form tools"),
    ("Config", "Vendor posting profiles", "PostingProfileHeaders", None, "ERP MCP form tools"),
    ("Config", "Payment terms", "PaymentTerms", None, "ERP MCP form/data tools"),
    ("Config", "Tax codes", "TaxCodes", None, "ERP MCP form/data tools"),
    ("Config", "Currencies", "Currencies", None, "ships with environment"),
    ("Config", "AP number sequence references", "NumberSequencesV2References",
     "ScopeValue eq '{c}'", "setup_fno_number_sequences.py"),
    ("Master", "Vendor groups", "VendorGroups", "dataAreaId eq '{c}'", "ERP MCP data tools"),
    ("Master", "Vendors", "VendorsV2", "dataAreaId eq '{c}'", "ERP MCP data tools"),
    ("Master", "Released products", "ReleasedProductsV2", "dataAreaId eq '{c}'", "ERP MCP data tools"),
    ("Master", "Purchase orders", "PurchaseOrderHeadersV2", "dataAreaId eq '{c}'", "ERP MCP data tools"),
    ("Txn", "Product receipts", "ProductReceiptHeaders", "dataAreaId eq '{c}'", "ERP MCP form/data tools"),
    ("Txn", "Vendor invoices", "VendorInvoiceHeaders", "dataAreaId eq '{c}'", "ERP MCP form/data tools"),
]

# Config items that must be present before a vendor invoice can be created/posted.
TXN_ENABLING = {
    "Ledger accounting currency", "Chart of accounts", "Main accounts",
    "Fiscal calendars", "Account structures", "Vendor posting profiles",
}


def _get(session, fno_url, coll, flt):
    url = f"{fno_url}/data/{coll}?$top=0&$count=true"
    if flt:
        url += f"&$filter={flt}"
    last = None
    for _ in range(5):
        try:
            r = session.get(url, timeout=90)
            if r.status_code == 200:
                return r.json().get("@odata.count", 0)
            return f"ERR{r.status_code}"
        except requests.exceptions.RequestException as exc:
            last = exc
            time.sleep(3)
    return f"ERR({last})"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--company", default=DEFAULT_COMPANY,
                    help="Legal entity (dataAreaId) to validate, default 'dat'.")
    args = ap.parse_args()

    auth.load_env(EPISODE)
    fno_url = os.environ["FNO_URL"].rstrip("/")
    token = auth.get_credential(EPISODE).get_token(f"{fno_url}/.default").token
    session = requests.Session()
    session.verify = False
    session.headers.update({"Authorization": f"Bearer {token}",
                            "Accept": "application/json"})

    print(f"F&O scaffold for legal entity '{args.company}'\n")
    print(f"{'LAYER':7} {'OBJECT':30} {'COUNT':>7}  {'STATUS':9} BUILT BY")
    missing_enabling = 0
    for layer, label, coll, flt, built_by in SCAFFOLD:
        f = flt.format(c=args.company) if flt else None
        count = _get(session, fno_url, coll, f)
        present = isinstance(count, int) and count > 0
        status = "present" if present else "MISSING"
        if not present and label in TXN_ENABLING:
            missing_enabling += 1
        print(f"{layer:7} {label:30} {str(count):>7}  {status:9} {built_by}")

    print()
    if missing_enabling:
        print(f"{missing_enabling} transaction-enabling Config item(s) missing: a "
              f"vendor invoice cannot be created in '{args.company}' until the "
              f"company is configured (ERP MCP form tools or demo data).")
        sys.exit(1)
    print(f"Config layer complete: '{args.company}' can create/post vendor invoices.")
    sys.exit(0)


if __name__ == "__main__":
    main()
