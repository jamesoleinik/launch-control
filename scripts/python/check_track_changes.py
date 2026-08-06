#!/usr/bin/env python
"""
Check Track Changes status on all lc_* custom tables in Dataverse.
Required for Dataverse-to-OneLake / Link data enablement.
"""

import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from auth import load_env, get_token  # noqa: E402


def _display_name(entity):
    dn = entity.get("DisplayName")
    if isinstance(dn, dict):
        user_label = dn.get("UserLocalizedLabel") or {}
        label = user_label.get("Label")
        if label:
            return label
        labels = dn.get("LocalizedLabels") or []
        if labels:
            return labels[0].get("Label", "")
    return entity.get("LogicalName", "")


def main():
    load_env(os.environ.get("LC_ENV"))
    dv_url = os.getenv("DATAVERSE_URL", "").rstrip("/")
    if not dv_url:
        print("ERROR: DATAVERSE_URL not set. Load .env or set LC_ENV.")
        return 1

    print(f"Connecting to: {dv_url}")

    try:
        access_token = get_token(os.environ.get("LC_ENV"))
    except Exception as exc:
        print(f"ERROR: token acquisition failed: {exc}")
        return 1

    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    # Do not server-filter with startswith() because some envs reject it for metadata.
    query_url = (
        f"{dv_url}/api/data/v9.2/EntityDefinitions"
        f"?$select=LogicalName,DisplayName,ChangeTrackingEnabled"
    )

    entities = []
    url = query_url
    try:
        while url:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            entities.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
    except requests.exceptions.RequestException as exc:
        print(f"ERROR: metadata query failed: {exc}")
        return 1

    lc_entities = [e for e in entities if (e.get("LogicalName") or "").startswith("lc_")]
    lc_entities.sort(key=lambda e: e.get("LogicalName", ""))

    if not lc_entities:
        print("WARNING: no lc_* custom tables found in this environment.")
        return 1

    print("\nCustom launch tables (lc_*) Track Changes status:\n")
    print(f"{'Table Name':<32} {'Display Name':<42} {'Track Changes':<15}")
    print("-" * 95)

    disabled = []
    for table in lc_entities:
        name = table.get("LogicalName", "")
        display = _display_name(table)
        enabled = bool(table.get("ChangeTrackingEnabled", False))
        status = "ENABLED" if enabled else "DISABLED"
        print(f"{name:<32} {display[:41]:<42} {status:<15}")
        if not enabled:
            disabled.append(name)

    if disabled:
        print(f"\n{len(disabled)} table(s) need Track Changes enabled:")
        for table in disabled:
            print(f"  - {table}")
        return 1

    print("\nAll custom launch tables have Track Changes enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
