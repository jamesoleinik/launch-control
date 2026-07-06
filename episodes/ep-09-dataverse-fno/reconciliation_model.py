"""Episode 9, Act 2: the ``lc_reconciliation`` trigger table.

This is the surface that turns the static launch-plus-procurement picture into an
**event-driven** chain. A recurring Finance & Operations batch (native X++, see
``fno-batch/``) or the scheduled orchestrator (``batch_reconcile.py``) writes one
``lc_reconciliation`` row per under-invoiced engagement. That row-create is what
fires the asynchronous Copilot Studio agent ("When a row is added -- Microsoft
Dataverse"), which reconciles the gap and writes back an outcome.

The table is kept deliberately separate from ``lc_vendorwork`` so the row-add
trigger fires **only** on batch output, never on an engagement edit.

  lc_launch   --< lc_reconciliation >-- lc_vendorwork
                        |
                        +-- committed / invoiced / gap, status Open -> Processed

Columns (all created with the ``lc_`` publisher prefix):

* ``lc_Name``           primary column, human label ("Reconcile PO-10502 ...").
* ``lc_SignalKey``      idempotency key (one open signal per PO run).
* ``lc_LaunchCode``     denormalized launch code for cheap filtering.
* ``lc_VendorAccount`` / ``lc_VendorName`` / ``lc_PONumber``   F&O business keys.
* ``lc_CommittedAmount`` / ``lc_InvoicedAmount`` / ``lc_GapAmount``   the money.
* ``lc_Status``         ``Open`` when the batch writes it, ``Processed`` when the
  agent has handled it.
* ``lc_AgentOutcome``   free text the agent writes back (what it did).
* ``lc_LaunchId``       lookup to ``lc_launch``.
* ``lc_VendorWorkId``   lookup to ``lc_vendorwork`` (the source engagement).

Idempotent: ``ensure_reconciliation_table`` skips anything that already exists, so
it is safe to import from the orchestrator and safe to re-run standalone:

    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/reconciliation_model.py
"""

import os
import sys
import time

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
from PowerPlatform.Dataverse.client import DataverseClient  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
SOLUTION = "LaunchControl"

TABLE = "lc_Reconciliation"
LOGICAL = "lc_reconciliation"
ENTITYSET = "lc_reconciliations"

# Simple columns only. The two lookups are added separately after the table
# exists (metadata propagation makes lookups flaky right after table creation).
COLUMNS = {
    "lc_SignalKey": "string",
    "lc_LaunchCode": "string",
    "lc_VendorAccount": "string",
    "lc_VendorName": "string",
    "lc_PONumber": "string",
    "lc_CommittedAmount": "decimal",
    "lc_InvoicedAmount": "decimal",
    "lc_GapAmount": "decimal",
    "lc_Status": "string",
    "lc_AgentOutcome": "memo",
}

# lookup logical name -> (target table, display name)
LOOKUPS = {
    "lc_launchid": ("lc_launch", "Launch"),
    "lc_vendorworkid": ("lc_vendorwork", "Vendor Work"),
}


def _column_names(client):
    cols = client.tables.list_columns(LOGICAL) or []
    return {
        (c.get("LogicalName") if isinstance(c, dict) else getattr(c, "LogicalName", None))
        for c in cols
    }


def _ensure_lookup(client, field, target, display_name):
    for attempt in range(8):
        try:
            client.tables.create_lookup_field(
                LOGICAL, field, target,
                display_name=display_name, solution=SOLUTION,
            )
            print(f"[ok]   lookup {LOGICAL}.{field} -> {target}")
            return
        except Exception as exc:  # noqa: BLE001 - retry on metadata lock/propagation
            msg = str(exc).lower()
            if "duplicate" in msg or "already exists" in msg:
                print(f"[skip] lookup {field} exists (race)")
                return
            wait = min(2 ** attempt, 30)
            print(f"       retry {attempt + 1}/8 in {wait}s ({str(exc)[:80]})")
            time.sleep(wait)
    raise RuntimeError(f"could not create {field} lookup")


def ensure_reconciliation_table(client):
    """Create lc_reconciliation (+ its two lookups) if missing. Idempotent."""
    if client.tables.get(TABLE):
        print(f"[skip] table {TABLE} exists")
    else:
        print(f"[create] {TABLE} ...")
        result = client.tables.create(
            TABLE, COLUMNS, solution=SOLUTION,
            primary_column="lc_Name", display_name="Reconciliation Signal",
        )
        print(f"[ok]   created {result['logical_name']} "
              f"(entity set {result['entity_set_name']}, "
              f"{result['columns_created']} columns)")

    names = _column_names(client)
    for field, (target, display_name) in LOOKUPS.items():
        if field in names:
            print(f"[skip] lookup {field} -> {target} exists")
        else:
            print(f"[create] lookup {LOGICAL}.{field} -> {target} ...")
            _ensure_lookup(client, field, target, display_name)


def ensure_change_tracking(url, token):
    """Enable change tracking on lc_reconciliation. Idempotent.

    The Copilot Studio / Dataverse "When a row is added" trigger only lists a
    table (and only fires reliably) when the table has change tracking enabled.
    A freshly created custom table has it off, so the trigger picker will not
    show lc_reconciliation until this runs.
    """
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    meta = requests.get(
        f"{url}/api/data/v9.2/EntityDefinitions(LogicalName='{LOGICAL}')"
        "?$select=LogicalName,ChangeTrackingEnabled",
        headers=h,
    ).json()
    if meta.get("ChangeTrackingEnabled") is True:
        print("[skip] change tracking already enabled")
        return
    metadata_id = meta["MetadataId"]
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "MetadataId": metadata_id,
        "LogicalName": LOGICAL,
        "ChangeTrackingEnabled": True,
        "HasChanged": True,
    }
    # Metadata updates must be a full PUT (partial PATCH is rejected with 405);
    # a minimal body plus MSCRM.MergeLabels is accepted.
    r = requests.put(
        f"{url}/api/data/v9.2/EntityDefinitions(MetadataId={metadata_id})",
        headers={**h, "MSCRM.MergeLabels": "true"},
        json=body,
    )
    if r.status_code not in (200, 204):
        raise RuntimeError(
            f"could not enable change tracking ({r.status_code}): {r.text[:300]}")
    pub = requests.post(
        f"{url}/api/data/v9.2/PublishXml",
        headers=h,
        json={"ParameterXml": f"<importexportxml><entities><entity>{LOGICAL}"
                              "</entity></entities></importexportxml>"},
    )
    if pub.status_code not in (200, 204):
        raise RuntimeError(f"publish failed ({pub.status_code}): {pub.text[:300]}")
    print("[ok]   change tracking enabled and published")


def main():
    auth.load_env(EPISODE)
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    print(f"Dataverse env: {url}\n")
    client = DataverseClient(url, auth.get_credential(EPISODE))
    ensure_reconciliation_table(client)
    ensure_change_tracking(url, auth.get_token(EPISODE))
    print("\nDone. lc_reconciliation is ready as the agent trigger surface.")


if __name__ == "__main__":
    main()
