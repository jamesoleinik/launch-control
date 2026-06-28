"""Ep 9 F&O readiness check.

Read-only probe of the Finance & Operations side of the Episode 9 environment.
It does NOT seed anything; it tells you whether the ERP half has the master and
transactional data the Launch ERP Readiness agent needs to produce its headline result
(budget, vendor PO, inventory for the launch SKU).

Why this is a check and not a seeder
------------------------------------
A freshly provisioned F&O environment ships with only the empty `dat` template
company and no initialized posting setup, so OData writes fail at the X++ layer
(a Currency POST returns HTTP 400 "Exception has been thrown by the target of an
invocation") and there is no demo company to load into. Real ERP data requires an
admin action, not a script:

  - Provision (or re-provision) the F&O environment WITH demo data, which deploys
    the Contoso / USMF dataset (Power Platform admin center / LCS, choose a demo
    data topology), OR
  - Import demo-data packages via the Data Management Framework into a fully
    initialized company (number sequences, posting profiles, ledger setup).

Run this after that admin step to confirm the env is recording-ready.

Usage (PowerShell):
    $env:LC_ENV = "ep-09-dataverse-fno"
    az login            # as an F&O admin for this environment
    python episodes/ep-09-dataverse-fno/fno_readiness.py

Exit code 0 = ready, 1 = not ready.
"""

from __future__ import annotations

import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from scripts import auth  # noqa: E402

# The entities the Ep 9 headline result reads, with a friendly label.
CHECKS = [
    ("Currencies", "currencies"),
    ("VendorsV2", "vendors"),
    ("ReleasedProductsV2", "released products"),
    ("CustomersV3", "customers"),
    ("PurchaseOrderHeadersV2", "purchase orders"),
    ("ProjectsV2", "projects"),
]


def _fno_token(fno_url: str) -> str:
    """Mint an Entra token for the F&O resource via the active az login."""
    from azure.identity import AzureCliCredential

    tenant = os.environ.get("TENANT_ID")
    cred = AzureCliCredential(tenant_id=tenant, process_timeout=60)
    return cred.get_token(f"{fno_url}/.default").token


def _count(fno_url: str, headers: dict, entity: str) -> int | None:
    url = f"{fno_url}/data/{entity}/$count?cross-company=true"
    r = requests.get(url, headers=headers, timeout=60)
    if r.status_code != 200:
        return None
    # The count body can carry a BOM; strip non-digits defensively.
    return int("".join(ch for ch in r.text if ch.isdigit()) or "0")


def main() -> int:
    auth.load_env(os.environ.get("LC_ENV", "ep-09-dataverse-fno"))
    fno_url = os.environ.get("FNO_URL", "").rstrip("/")
    if not fno_url:
        print("FAIL: FNO_URL is not set. Add it to the episode .env "
              "(for example https://<your-fno-env>.operations.dynamics.com).")
        return 1

    print(f"F&O endpoint: {fno_url}")
    try:
        token = _fno_token(fno_url)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: could not acquire an F&O token ({exc}). "
              f"Run `az login` as an F&O admin for this environment.")
        return 1

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    ready = True
    print("\nMaster / transactional data:")
    for entity, label in CHECKS:
        n = _count(fno_url, headers, entity)
        if n is None:
            print(f"  ?  {label:<18} ({entity}): not reachable")
            ready = False
        elif n == 0:
            print(f"  x  {label:<18} ({entity}): 0")
            ready = False
        else:
            print(f"  ok {label:<18} ({entity}): {n}")

    print()
    if ready:
        print("PASS: F&O has data for the Ep 9 headline result.")
        return 0
    print("NOT READY: the ERP half is empty or unreachable. Provision the F&O "
          "environment WITH demo data (admin center / LCS demo topology), or "
          "import demo-data packages via the Data Management Framework, then "
          "re-run this check. See the module docstring for details.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
