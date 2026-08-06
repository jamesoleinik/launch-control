#!/usr/bin/env python
"""
Enable Track Changes on all lc_* custom tables in Dataverse.
Required for Dataverse-to-OneLake link.

Usage:
  python scripts/python/enable_track_changes.py --dry-run   # preview changes
  python scripts/python/enable_track_changes.py --apply      # apply changes
"""

import os
import sys
import argparse
import requests
from pathlib import Path

# Add scripts/ to path for auth module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from auth import get_credential, load_env, get_token
from PowerPlatform.Dataverse.client import DataverseClient

def main():
    parser = argparse.ArgumentParser(
        description='Enable Track Changes on all lc_* custom tables in Dataverse'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying them')
    parser.add_argument('--apply', action='store_true', help='Apply Track Changes enablement')
    args = parser.parse_args()

    # Load environment
    load_env()
    dv_url = os.environ.get('DATAVERSE_URL', '').rstrip('/')
    if not dv_url:
        print("❌ DATAVERSE_URL not set")
        sys.exit(1)

    print(f"🔗 Connecting to: {dv_url}\n")

    # Get token for Web API
    try:
        token = get_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'OData-Version': '4.0',
            'OData-MaxVersion': '4.0'
            }
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # Use SDK to get metadata
    try:
        credential = get_credential()
        client = DataverseClient(dv_url, credential)
    except Exception as e:
        print(f"❌ Failed to create client: {e}")
        sys.exit(1)

    # Query all lc_* tables
    print("📋 Querying lc_* tables...\n")
    lc_tables = [
        'lc_launch', 'lc_milestone', 'lc_task', 'lc_statusupdate', 'lc_teammember',
        'lc_erpsignal',  # Ep 9 stand-in
        'lc_stg_tracker_a', 'lc_stg_tracker_b', 'lc_stg_tracker_c', 'lc_stg_tracker_d', 'lc_stg_tracker_e'  # Ep 3 staging
    ]

    disabled_tables = []
    table_ids = {}
    print(f"{'Table Name':<30} {'Track Changes':<15}")
    print("-" * 45)

    for table_name in lc_tables:
        try:
            table_info = client.tables.get(table_name)
            if table_info:
                enabled = getattr(table_info, 'ChangeTrackingEnabled', False)
                status = "✓ ENABLED" if enabled else "❌ DISABLED"
                print(f"{table_name:<30} {status:<15}")
                if not enabled:
                    disabled_tables.append(table_name)
                    # Get metadata ID from table
                    table_ids[table_name] = getattr(table_info, 'MetadataId', None)
        except Exception as e:
            print(f"{table_name:<30} ⚠ QUERY FAILED: {str(e)[:30]}")

    if not disabled_tables:
        print("\n✓ All tables already have Track Changes enabled!")
        return 0

    print(f"\n⚠ {len(disabled_tables)} table(s) need Track Changes enabled\n")

    if args.dry_run:
        print("🔍 DRY-RUN MODE: No changes will be applied")
        print("   To apply changes, run:")
        print("   python scripts/python/enable_track_changes.py --apply\n")
        return 0

    if not args.apply:
        print("⚠ Specify --apply to enable Track Changes, or --dry-run to preview")
        return 1

    # Apply changes via Web API
    print("⚙️ Enabling Track Changes via Web API...\n")
    successes = 0
    failures = 0

    for table_name in disabled_tables:
        try:
            # Query table metadata to get its ID
            metadata_url = f"{dv_url}/api/data/v9.2/EntityDefinitions(LogicalName='{table_name}')"
            resp = requests.get(metadata_url, headers=headers, timeout=10)
            resp.raise_for_status()
            table_meta = resp.json()
            table_id = table_meta.get('MetadataId')
            
            if not table_id:
                print(f"✗ {table_name}: Could not retrieve MetadataId")
                failures += 1
                continue
            
            # Update ChangeTrackingEnabled
            update_url = f"{dv_url}/api/data/v9.2/EntityDefinitions({table_id})"
            update_headers = headers.copy()
            update_headers['If-Match'] = '*'
            update_resp = requests.patch(
                update_url,
                headers=update_headers,
                json={"ChangeTrackingEnabled": True},
                timeout=30
            )

            if update_resp.status_code in (200, 204):
                print(f"✓ {table_name}: Track Changes enabled")
                successes += 1
            else:
                print(f"✗ {table_name}: HTTP {update_resp.status_code}")
                failures += 1
        except Exception as e:
            print(f"✗ {table_name}: {str(e)[:60]}")
            failures += 1

    # Summary
    print()
    if failures == 0:
        print(f"✓ {successes} table(s) updated successfully!")
        print("  You can now proceed with the Dataverse-to-OneLake link in Fabric.")
        return 0
    else:
        print(f"⚠ {successes} succeeded, {failures} failed")
        print("  Review errors above and retry with --apply")
        return 1

if __name__ == '__main__':
    sys.exit(main())


