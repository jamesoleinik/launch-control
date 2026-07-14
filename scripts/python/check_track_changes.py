#!/usr/bin/env python
"""
Check Track Changes status on all lc_* custom tables in Dataverse.
Required for Dataverse-to-OneLake link enablement.
"""

import os
import json
import sys
import subprocess
import requests

def main():
    dv_url = os.getenv('DATAVERSE_URL', '').rstrip('/')
    if not dv_url:
        print("❌ DATAVERSE_URL not set. Load .env or set via LC_ENV")
        sys.exit(1)

    print(f"🔗 Connecting to: {dv_url}")

    # Authenticate via az login context
    try:
        token_resp = subprocess.run(
            ['az', 'account', 'get-access-token', '--resource', dv_url],
            capture_output=True, text=True, check=True
        )
        token_data = json.loads(token_resp.stdout)
        access_token = token_data['accessToken']
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        sys.exit(1)

    # Query metadata: all tables with logical name starting with 'lc_'
    query_url = (
        f"{dv_url}/api/data/v9.2/EntityDefinitions"
        f"?$filter=startswith(LogicalName,'lc_')"
        f"&$select=LogicalName,DisplayName,ChangeTrackingEnabled"
    )

    try:
        resp = requests.get(query_url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        print("\n📋 Custom Launch Tables (lc_*) — Track Changes Status:\n")
        print(f"{'Table Name':<30} {'Display Name':<40} {'Track Changes':<15}")
        print("-" * 85)

        disabled = []
        for table in data.get('value', []):
            name = table['LogicalName']
            display = table.get('DisplayName', name)
            enabled = table.get('ChangeTrackingEnabled', False)
            status = "✓ ENABLED" if enabled else "❌ DISABLED"
            print(f"{name:<30} {display:<40} {status:<15}")
            if not enabled:
                disabled.append(name)

        if disabled:
            print(f"\n⚠ {len(disabled)} table(s) need Track Changes enabled:")
            for t in disabled:
                print(f"  - {t}")
            return 1
        else:
            print("\n✓ All custom launch tables have Track Changes enabled!")
            return 0

    except requests.exceptions.RequestException as e:
        print(f"❌ Query failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    sys.exit(main())
