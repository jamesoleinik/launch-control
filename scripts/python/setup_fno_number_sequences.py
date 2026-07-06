"""Provision the Accounts Payable vendor-invoice number sequences for a Finance &
Operations legal entity, programmatically, over the F&O OData API.

Why this script exists
----------------------
The `dat` legal entity in this build was stood up nearly bare: it has almost no
number sequences. In Dynamics 365 F&O you cannot create (or post) a record for a
reference until a number sequence is set up and associated with that reference, so
"New vendor invoice" fails in the app with:

    Numbers could not be generated because a number sequence reference is missing.

The supported UI fix is the "Generate number sequences" wizard. This script is the
programmatic equivalent. It is fully data-driven over OData:

  1. Number sequence CODE  -> entity set `SequenceV2Tables`
     (the `NumberSequenceTableV2Entity`; note the OData collection name drops the
     `Number` prefix, which is why it is easy to miss in `$metadata`).
  2. Number sequence REFERENCE that binds a datatype to a code, per legal entity
     -> entity set `NumberSequencesV2References`.

Creating a reference requires the code to exist first, so each code is created
before its reference. `InUse` is a computed field and must not be sent on insert.

The number sequence code table is NOT exposed to record CRUD through the Dataverse
MCP / virtual-entity path; it is an F&O OData (and Data Management) entity. That is
why this provisioning runs against the F&O OData surface, not the Dataverse MCP.

Idempotent and dry-run first
----------------------------
Re-running is safe: existing codes and references are detected and skipped. Preview
everything with --dry-run before applying.

Run (preview):
    $env:PYTHONIOENCODING="utf-8"
    python scripts/python/setup_fno_number_sequences.py --dry-run

Run (apply):
    python scripts/python/setup_fno_number_sequences.py

The legal entity defaults to `dat` and can be overridden with --company.
"""

import argparse
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
DEFAULT_COMPANY = "dat"

# The vendor-invoice number sequences needed to create and post a PO-based vendor
# invoice. Each entry provisions one code (SequenceV2Tables) and one reference
# (NumberSequencesV2References) that binds the F&O datatype to that code.
#
#   datatype  : the NumberSequenceDataType name the AP module resolves at runtime
#   code      : a legal-entity-scoped number sequence code (unique within scope)
#   prefix    : the constant segment of the format (format is "<prefix>-######")
#   name      : the human label shown on the Number sequences page
NUMBER_SEQUENCES = [
    {
        "datatype": "PurchInternalInvoiceId",
        "code": "Vinv_1",
        "prefix": "VINV",
        "name": "LC vendor invoice",
    },
    {
        "datatype": "PurchInvoiceVoucher",
        "code": "Vvch_1",
        "prefix": "VVCH",
        "name": "LC vendor invoice voucher",
    },
    {
        "datatype": "PurchInternalPackingSlipId",
        "code": "Vpsl_1",
        "prefix": "VPSL",
        "name": "LC product receipt",
    },
    {
        "datatype": "PurchPackingSlipVoucher",
        "code": "Vpsv_1",
        "prefix": "VPSV",
        "name": "LC product receipt voucher",
    },
    {
        "datatype": "PurchInternalCreditNoteId",
        "code": "Vcrn_1",
        "prefix": "VCRN",
        "name": "LC vendor credit note",
    },
    {
        "datatype": "PurchCreditNoteVoucher",
        "code": "Vcnv_1",
        "prefix": "VCNV",
        "name": "LC vendor credit note voucher",
    },
    {
        "datatype": "PurchaseOrderVoucher",
        "code": "Vpov_1",
        "prefix": "VPOV",
        "name": "LC purchase order voucher",
    },
]


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


def code_exists(session, fno_url, code, company):
    flt = f"NumberSequenceCode eq '{code}' and ScopeValue eq '{company}'"
    r = _fno_call(session, fno_url, "GET",
                  f"SequenceV2Tables?$filter={flt}&$top=1")
    return r.status_code == 200 and bool(r.json().get("value"))


def reference_exists(session, fno_url, datatype, company):
    flt = f"DataTypeName eq '{datatype}' and ScopeValue eq '{company}'"
    r = _fno_call(session, fno_url, "GET",
                  f"NumberSequencesV2References?$filter={flt}&$top=1")
    return r.status_code == 200 and bool(r.json().get("value"))


def build_code_payload(entry, company):
    prefix = entry["prefix"]
    # AnnotatedFormat encodes the segments as "<ordinal>\t<value>" lines, mirroring
    # how F&O stores a "<constant>-<number>" format (see an existing dat code).
    annotated = f"0\t{prefix}\n-1\t-\n-2\t######"
    return {
        "NumberSequenceCode": entry["code"],
        "ScopeType": "DataArea",
        "ScopeValue": company,
        "Company": company,
        "Name": entry["name"],
        "Format": f"{prefix}-######",
        "AnnotatedFormat": annotated,
        "Continuous": "No",
        "Manual": "No",
        "Stopped": "No",
        "Next": 1,
        "Smallest": 1,
        "Largest": 999999,
        "QuantityOfNumbers": 5,
        "Preallocation": "Yes",
        "ToAHigherNumber": "No",
        "ToALowerNumber": "No",
        "Cyclical": "No",
        "SkipCounting": "No",
        "CleanUp": "No",
        "Interval": 0,
        "OperatingUnitTypes": "None",
    }


def build_reference_payload(entry, company):
    return {
        "ScopeType": "DataArea",
        "ScopeValue": company,
        "DataTypeName": entry["datatype"],
        "NumberSequenceCode": entry["code"],
        "ReuseNumbers": "No",
    }


def provision(session, fno_url, company, dry_run):
    created_codes = created_refs = skipped = failed = 0
    for entry in NUMBER_SEQUENCES:
        code, datatype = entry["code"], entry["datatype"]

        if code_exists(session, fno_url, code, company):
            print(f"[skip] code {code} already exists in {company}")
        elif dry_run:
            print(f"[dry ] would create code {code} "
                  f"(format {entry['prefix']}-######) in {company}")
        else:
            r = _fno_call(session, fno_url, "POST", "SequenceV2Tables",
                          json=build_code_payload(entry, company))
            if r.status_code in (200, 201):
                print(f"[ok]   created code {code} in {company}")
                created_codes += 1
            else:
                print(f"[FAIL] code {code} -> {r.status_code}: {r.text[:200]}")
                failed += 1
                continue

        if reference_exists(session, fno_url, datatype, company):
            print(f"[skip] reference {datatype} already bound in {company}")
            skipped += 1
        elif dry_run:
            print(f"[dry ] would bind reference {datatype} -> {code} in {company}")
        else:
            r = _fno_call(session, fno_url, "POST", "NumberSequencesV2References",
                          json=build_reference_payload(entry, company))
            if r.status_code in (200, 201):
                print(f"[ok]   bound reference {datatype} -> {code} in {company}")
                created_refs += 1
            else:
                print(f"[FAIL] reference {datatype} -> {r.status_code}: {r.text[:200]}")
                failed += 1

    print(f"\nSummary: {created_codes} code(s) created, {created_refs} reference(s) "
          f"bound, {skipped} already present, {failed} failed.")
    return failed == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--company", default=DEFAULT_COMPANY,
                    help="Legal entity (dataAreaId) to provision, default 'dat'.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Preview the changes without writing.")
    args = ap.parse_args()

    auth.load_env(EPISODE)
    fno_url = os.environ["FNO_URL"].rstrip("/")
    fno_token = auth.get_credential(EPISODE).get_token(f"{fno_url}/.default").token
    session = fno_session(fno_token)

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"Provisioning AP vendor-invoice number sequences in "
          f"'{args.company}' [{mode}]\n")
    ok = provision(session, fno_url, args.company, args.dry_run)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
