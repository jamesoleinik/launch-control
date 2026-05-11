"""Episode 11 preflight: verify the demo env is in the state Ep 11 needs.

Ep 11 = `dv-admin` skill demo. Five commands; the env state required:
  - >= 10 pre-Q1 lc_statusupdate rows tagged `[PRE-Q1-SEED]` exist
    (so the FetchXML cleanup beat has data to delete on camera)
  - >= 1 lc_launch with the demo subject exists (for narrative anchor)
  - lc_statusupdate table is solution-tracked & queryable

Does NOT verify (these are user actions documented in episode-11.md):
  - dv-admin skill installed/loadable in Copilot CLI
  - audit-setting / plugin-trace-setting drift exists between two scopes
  - Second-environment vs two-table fallback decision

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
TOK = get_credential().get_token(URL + '/.default').token
H = {'Authorization': 'Bearer ' + TOK, 'Accept': 'application/json'}

TAG = 'PreQ1Seed::'
LAUNCH_NAME = os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch')


def fetch(p):
    out, full = [], URL + p
    while full:
        r = requests.get(full, headers=H); r.raise_for_status()
        j = r.json(); out += j.get('value', [])
        full = j.get('@odata.nextLink')
    return out


def check(name, ok, detail=''):
    print(f"  [{'PASS' if ok else 'FAIL'}]  {name}{(' -- ' + detail) if detail else ''}")
    return ok


def main():
    print("Episode 11 preflight\n")
    failures = 0

    safe_name = LAUNCH_NAME.replace("'", "''")
    launches = fetch(f"/api/data/v9.2/lc_launchs?$select=lc_launchid"
                     f"&$filter=lc_name eq '{safe_name}'")
    if not check(f"Launch '{LAUNCH_NAME}' exists", len(launches) == 1,
                 f"got {len(launches)}"):
        failures += 1

    seeded = fetch(f"/api/data/v9.2/lc_statusupdates?$select=lc_statusupdateid,createdon,lc_title"
                   f"&$filter=startswith(lc_title,'{TAG}')")
    if not check("Pre-Q1 seeded status updates >= 10", len(seeded) >= 10,
                 f"got {len(seeded)}"):
        failures += 1
        print(f"      Run: python scripts/python/seed_pre_q1_status_updates.py")

    if seeded:
        pre_q1 = [r for r in seeded if (r.get('createdon') or '') < '2026-01-01']
        if not check("Every seeded row has createdon < 2026-01-01",
                     len(pre_q1) == len(seeded),
                     f"{len(pre_q1)}/{len(seeded)} pre-Q1"):
            failures += 1

    sus = fetch("/api/data/v9.2/lc_statusupdates?$select=lc_statusupdateid&$top=1")
    if not check("lc_statusupdate table queryable", len(sus) >= 1,
                 f"got {len(sus)} sample"):
        failures += 1

    print()
    if failures == 0:
        print("ALL GREEN -- env data is ready for the dv-admin demo.")
        print()
        print("REMAINING (manual checks before recording):")
        print("  - /plugin list in Copilot CLI confirms dv-admin installed")
        print("  - Audit setting drift exists between chosen scopes")
        print("  - All 5 commands rehearsed end-to-end against demo env")
        return 0
    print(f"{failures} FAILURE(S) -- fix before recording.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
