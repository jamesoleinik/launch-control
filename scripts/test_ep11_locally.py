"""Episode 11 preflight: verify the demo env is in the state Ep 11 needs.

Ep 11 = administration/management plane is agent-driven. Five proof points:
  1. Auditing on by conversation
  2. Capacity by conversation       <-- new (replaces drift-compare beat)
  3. Bulk cleanup, auditable not destructive (FetchXML preview + confirm)
  4. Agent blast-radius is one prompt
  5. The chat is the audit log

This script verifies the env data and admin API reachability needed for the demo.
Run: python scripts/test_ep11_locally.py
"""
import os, sys
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv
from auth import get_credential

load_dotenv(os.path.join(ROOT, '.env'))
URL = os.environ['DATAVERSE_URL']
DEMO_ENV_NAME = os.environ.get('LAUNCH_CONTROL_ENV_NAME', 'Product Launch')
TAG = 'PreQ1Seed::'
LAUNCH_NAME = os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch')

CRED = get_credential()
DV_TOK = CRED.get_token(URL + '/.default').token
DV_H = {'Authorization': 'Bearer ' + DV_TOK, 'Accept': 'application/json'}

BAP = 'https://api.bap.microsoft.com'


def fetch(p):
    out, full = [], URL + p
    while full:
        r = requests.get(full, headers=DV_H); r.raise_for_status()
        j = r.json(); out += j.get('value', [])
        full = j.get('@odata.nextLink')
    return out


def check(name, ok, detail=''):
    print(f"  [{'PASS' if ok else 'FAIL'}]  {name}{(' -- ' + detail) if detail else ''}")
    return ok


def main():
    print("Episode 11 preflight\n")
    failures = 0

    # ---- proof point 3 (cleanup) data shape ----
    safe_name = LAUNCH_NAME.replace("'", "''")
    launches = fetch(f"/api/data/v9.2/lc_launchs?$select=lc_launchid"
                     f"&$filter=lc_name eq '{safe_name}'")
    if not check(f"Launch '{LAUNCH_NAME}' exists", len(launches) == 1,
                 f"got {len(launches)}"):
        failures += 1

    seeded = fetch(f"/api/data/v9.2/lc_statusupdates?$select=lc_statusupdateid,createdon,lc_title"
                   f"&$filter=startswith(lc_title,'{TAG}')")
    if not check("Pre-Q1 seeded status updates >= 10 (cleanup beat)",
                 len(seeded) >= 10, f"got {len(seeded)}"):
        failures += 1
        print("      Run: python scripts/python/seed_pre_q1_status_updates.py")

    if seeded:
        pre_q1 = [r for r in seeded if (r.get('createdon') or '') < '2026-01-01']
        if not check("Every seeded row has createdon < 2026-01-01",
                     len(pre_q1) == len(seeded),
                     f"{len(pre_q1)}/{len(seeded)} pre-Q1"):
            failures += 1

    # ---- proof point 2 (capacity) API reachability ----
    try:
        bap_tok = CRED.get_token('https://api.bap.microsoft.com/.default').token
        r = requests.get(
            f'{BAP}/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments'
            f'?api-version=2020-06-01',
            headers={'Authorization': 'Bearer ' + bap_tok})
        envs = r.json().get('value', []) if r.status_code == 200 else []
        check("BAP admin API reachable", r.status_code == 200,
              f"HTTP {r.status_code}, {len(envs)} envs visible")
        if r.status_code != 200:
            failures += 1

        target = next((e for e in envs
                       if e.get('properties', {}).get('displayName') == DEMO_ENV_NAME), None)
        if not check(f"Demo env '{DEMO_ENV_NAME}' visible", target is not None,
                     f"searched {len(envs)} envs"):
            failures += 1
        else:
            r2 = requests.get(
                f'{BAP}/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/'
                f'{target["name"]}?$expand=properties.capacity&api-version=2020-06-01',
                headers={'Authorization': 'Bearer ' + bap_tok})
            cap = r2.json().get('properties', {}).get('capacity', []) if r2.status_code == 200 else []
            if not check("Capacity endpoint returns data", len(cap) >= 3,
                         f"got {len(cap)} pools"):
                failures += 1
            elif any((c.get('actualConsumption') or 0) / (c.get('ratedConsumption') or 1) >= 0.95
                     for c in cap if c.get('ratedConsumption')):
                hot = [c['capacityType'] for c in cap
                       if c.get('ratedConsumption') and
                       (c['actualConsumption'] / c['ratedConsumption']) >= 0.95]
                print(f"      [INFO] At-cap pools (great on-camera moment): {hot}")
    except Exception as e:
        check("BAP admin API reachable", False, f"exception: {e}")
        failures += 1

    print()
    if failures == 0:
        print("ALL GREEN -- env data + capacity API both ready.")
        print()
        print("REMAINING (manual checks before recording):")
        print("  - Pick the agent runtime: Copilot CLI w/ awesome-copilot dataverse plugin")
        print("    (driven by scripts/python/admin/*.py); decide whether to add a")
        print("    dedicated dv-admin skill or just call Python from the agent")
        print("  - All 5 prompts rehearsed end-to-end against demo env")
        return 0
    print(f"{failures} FAILURE(S) -- fix before recording.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
