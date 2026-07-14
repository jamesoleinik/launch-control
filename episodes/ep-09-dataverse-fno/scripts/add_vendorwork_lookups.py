"""Add real lookup relationships from lc_vendorwork to the live F&O virtual tables.

Episode 9. The lc_vendorwork join originally stored the Finance & Operations keys
(lc_vendoraccount, lc_ponumber) as plain text, so a model-driven app showed no
related F&O detail. This adds two N:1 lookups from lc_vendorwork (a standard table)
to the generated F&O virtual tables, which is the supported direction (standard ->
virtual; cascades must be None). It then binds the six seeded WIDGET-Q3 rows to their
real virtual vendor and purchase-order records so the related detail resolves on the
form.

    lc_vendorwork.lc_VendorRef -> mserp_vendvendorv2entity            (by VendorAccountNumber)
    lc_vendorwork.lc_PORef     -> mserp_purchpurchaseorderheaderv2entity (by PurchaseOrderNumber)

The plain-text keys are kept: they remain the durable join over the SQL / TDS
endpoint (which does not expose virtual entities) and the fallback when the mserp_
virtual tables are not generated. The lookups are additive.

Idempotent and dry-run first:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/scripts/add_vendorwork_lookups.py --dry-run
    python episodes/ep-09-dataverse-fno/scripts/add_vendorwork_lookups.py
"""

import os
import sys
import time
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
SOLUTION = "LaunchControl"
API = "api/data/v9.2"

# Referencing (standard) table.
REFERENCING = "lc_vendorwork"
REFERENCING_SET = "lc_vendorworks"

# One spec per lookup: schema names, the F&O virtual target, and how to resolve a
# target record from the plain-text key already on lc_vendorwork.
LOOKUPS = [
    {
        "rel_schema": "lc_vendorwork_VendorRef",
        "lookup_schema": "lc_VendorRef",
        "display": "F&O Vendor",
        "referenced_entity": "mserp_vendvendorv2entity",
        "referenced_set": "mserp_vendvendorv2entities",
        "referenced_pk": "mserp_vendvendorv2entityid",
        "match_field": "mserp_vendoraccountnumber",
        "source_key": "lc_vendoraccount",
    },
    {
        "rel_schema": "lc_vendorwork_PORef",
        "lookup_schema": "lc_PORef",
        "display": "F&O Purchase Order",
        "referenced_entity": "mserp_purchpurchaseorderheaderv2entity",
        "referenced_set": "mserp_purchpurchaseorderheaderv2entities",
        "referenced_pk": "mserp_purchpurchaseorderheaderv2entityid",
        "match_field": "mserp_purchaseordernumber",
        "source_key": "lc_ponumber",
    },
]


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }


def _lookup_exists(url, h, lookup_schema):
    """True if a lookup attribute with this schema name is already on lc_vendorwork."""
    q = (
        f"{url}/{API}/EntityDefinitions(LogicalName='{REFERENCING}')/Attributes/"
        f"Microsoft.Dynamics.CRM.LookupAttributeMetadata"
        f"?$select=SchemaName&$filter=SchemaName eq '{lookup_schema}'"
    )
    r = requests.get(q, headers=h, timeout=90)
    return bool(r.status_code == 200 and r.json().get("value"))


def _create_lookup(url, h, spec, dry_run):
    if _lookup_exists(url, h, spec["lookup_schema"]):
        print(f"[skip] lookup {spec['lookup_schema']} already exists")
        return
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": spec["rel_schema"],
        "ReferencedEntity": spec["referenced_entity"],
        "ReferencingEntity": REFERENCING,
        "CascadeConfiguration": {
            "Assign": "NoCascade",
            "Delete": "RemoveLink",
            "Merge": "NoCascade",
            "Reparent": "NoCascade",
            "Share": "NoCascade",
            "Unshare": "NoCascade",
        },
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": spec["lookup_schema"],
            "DisplayName": {
                "@odata.type": "Microsoft.Dynamics.CRM.Label",
                "LocalizedLabels": [{
                    "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                    "Label": spec["display"], "LanguageCode": 1033,
                }],
            },
            "RequiredLevel": {
                "@odata.type": "Microsoft.Dynamics.CRM.AttributeRequiredLevelManagedProperty",
                "Value": "None",
            },
        },
    }
    if dry_run:
        print(f"[dry-run] would create lookup {spec['lookup_schema']} "
              f"({REFERENCING} -> {spec['referenced_entity']})")
        return
    hh = dict(h)
    hh["MSCRM.SolutionUniqueName"] = SOLUTION
    r = requests.post(f"{url}/{API}/RelationshipDefinitions", headers=hh,
                      json=body, timeout=120)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"create {spec['lookup_schema']} failed "
                           f"{r.status_code}: {r.text[:400]}")
    print(f"[ok]   created lookup {spec['lookup_schema']} "
          f"-> {spec['referenced_entity']}")
    # Wait for the lookup attribute to propagate before binding rows.
    for _ in range(15):
        if _lookup_exists(url, h, spec["lookup_schema"]):
            return
        time.sleep(4)
    print(f"[warn] {spec['lookup_schema']} not yet visible; binding may need a re-run")


def _resolve_target_id(url, h, spec, key_value, cache):
    """Return the virtual entity record GUID for a plain-text key (cached)."""
    ck = (spec["referenced_set"], key_value)
    if ck in cache:
        return cache[ck]
    q = (f"{url}/{API}/{spec['referenced_set']}"
         f"?$select={spec['referenced_pk']}"
         f"&$filter={spec['match_field']} eq '{key_value}'")
    r = requests.get(q, headers=h, timeout=90)
    val = r.json().get("value", []) if r.status_code == 200 else []
    gid = val[0][spec["referenced_pk"]] if val else None
    cache[ck] = gid
    return gid


def _bind_rows(url, h, spec, dry_run):
    """Set the lookup on every lc_vendorwork row from its plain-text key."""
    value_col = f"_{spec['lookup_schema'].lower()}_value"
    has_lookup = _lookup_exists(url, h, spec["lookup_schema"])
    select = f"lc_vendorworkid,lc_workkey,{spec['source_key']}"
    if has_lookup:
        select += f",{value_col}"
    q = f"{url}/{API}/{REFERENCING_SET}?$select={select}"
    r = requests.get(q, headers=h, timeout=90)
    rows = r.json().get("value", []) if r.status_code == 200 else []
    cache = {}
    bound = skipped = missing = 0
    for row in rows:
        key_value = row.get(spec["source_key"])
        if not key_value:
            continue
        if has_lookup and row.get(value_col):
            skipped += 1
            continue
        gid = _resolve_target_id(url, h, spec, key_value, cache)
        if not gid:
            print(f"[warn] no {spec['referenced_entity']} for "
                  f"{key_value} (row {row.get('lc_workkey')})")
            missing += 1
            continue
        if dry_run:
            print(f"[dry-run] would bind {row.get('lc_workkey')} "
                  f"{spec['lookup_schema']} -> {key_value}")
            bound += 1
            continue
        patch = {f"{spec['lookup_schema']}@odata.bind":
                 f"/{spec['referenced_set']}({gid})"}
        pr = requests.patch(
            f"{url}/{API}/{REFERENCING_SET}({row['lc_vendorworkid']})",
            headers=h, json=patch, timeout=90)
        if pr.status_code not in (200, 204):
            print(f"[warn] bind {row.get('lc_workkey')} failed "
                  f"{pr.status_code}: {pr.text[:200]}")
            continue
        print(f"[ok]   bound {row.get('lc_workkey'):10} "
              f"{spec['lookup_schema']} -> {key_value}")
        bound += 1
    print(f"       {spec['lookup_schema']}: {bound} bound, {skipped} already set, "
          f"{missing} unresolved")


def apply_lookups(url, token, dry_run=False):
    """Create the two virtual-table lookups and bind the seeded rows. Idempotent."""
    h = _headers(token)
    for spec in LOOKUPS:
        print(f"== {spec['lookup_schema']} ({REFERENCING} -> "
              f"{spec['referenced_entity']}) ==")
        _create_lookup(url, h, spec, dry_run)
        _bind_rows(url, h, spec, dry_run)
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="preview metadata + binds without writing")
    args = ap.parse_args()

    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = auth.get_token(EPISODE)
    print(f"Dataverse env: {url}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'APPLY'}\n")
    apply_lookups(url, token, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
