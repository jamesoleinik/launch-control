"""Episode 12 preflight: verify orchestra demo readiness.

Ep 12 = the 'Full Orchestra + Your Turn' closer. Six checks:
  1. The 3 orchestra scripts import + run --dry-run cleanly
  2. The lc_CalculateLaunchReadiness custom action exists (binding=0 unbound)
  3. Q3 Widget Launch exists and is reachable
  4. Capacity API is reachable (Ep 11 carryover -- Ep 12 may show capacity in montage)
  5. No 'Q4 Holiday Feature' launch exists yet (the teaser must create it on camera)
  6. OSS readiness files present at repo root: LICENSE, README.md, CHANGELOG.md, .env.example

Run: python scripts/test_ep12_locally.py
"""
from __future__ import annotations
import importlib, os, subprocess, sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv  # noqa: E402
from auth import get_credential  # noqa: E402

load_dotenv(os.path.join(ROOT, '.env'))
URL = os.environ['DATAVERSE_URL']
LAUNCH = os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch')
TEASER = 'Q4 Holiday Feature'

CRED = get_credential()
DV_TOK = CRED.get_token(URL + '/.default').token
DV_H = {'Authorization': 'Bearer ' + DV_TOK, 'Accept': 'application/json'}


def fetch(p):
    r = requests.get(URL + p, headers=DV_H); r.raise_for_status()
    return r.json().get('value', [])


def check(name, ok, detail=''):
    print(f"  [{'PASS' if ok else 'FAIL'}]  {name}{(' -- ' + detail) if detail else ''}")
    return ok


def main():
    print("Episode 12 preflight\n")
    failures = 0

    # ---- 1: orchestra scripts dry-run cleanly ----
    for script in ['setup_launch_week.py', 'teardown_launch_week.py']:
        path = os.path.join(ROOT, 'scripts', 'python', 'orchestra', script)
        try:
            r = subprocess.run([sys.executable, path, '--dry-run'],
                               capture_output=True, text=True, timeout=60)
            ok = r.returncode == 0 and 'DRY RUN COMPLETE' in r.stdout
            tail = (r.stderr or r.stdout).strip().splitlines()[-1] if not ok else ''
            if not check(f"{script} --dry-run", ok, tail[:120]):
                failures += 1
        except Exception as e:
            check(f"{script} --dry-run", False, str(e)); failures += 1

    spin = os.path.join(ROOT, 'scripts', 'python', 'orchestra', 'spin_up_launch.py')
    try:
        r = subprocess.run([sys.executable, spin, TEASER, '--dry-run'],
                           capture_output=True, text=True, timeout=60)
        ok = r.returncode == 0 and 'DRY RUN COMPLETE' in r.stdout
        if not check(f"spin_up_launch.py '{TEASER}' --dry-run", ok,
                     (r.stderr or r.stdout).strip().splitlines()[-1][:120] if not ok else ''):
            failures += 1
    except Exception as e:
        check("spin_up_launch.py --dry-run", False, str(e)); failures += 1

    # ---- 2: readiness custom action exists ----
    try:
        capis = fetch("/api/data/v9.2/customapis"
                      "?$select=name,uniquename,bindingtype"
                      "&$filter=name eq 'lc_CalculateLaunchReadiness'")
        if not check("Custom action lc_CalculateLaunchReadiness present",
                     len(capis) == 1, f"got {len(capis)}"):
            failures += 1
        elif capis[0].get('bindingtype') != 0:
            check("  ...is unbound (binding=0)", False,
                  f"got binding={capis[0].get('bindingtype')}"); failures += 1
    except Exception as e:
        check("Custom action lc_CalculateLaunchReadiness present", False, str(e))
        failures += 1

    # ---- 3: demo launch exists ----
    safe = LAUNCH.replace("'", "''")
    rows = fetch(f"/api/data/v9.2/lc_launchs?$select=lc_launchid"
                 f"&$filter=lc_name eq '{safe}'")
    if not check(f"Launch '{LAUNCH}' exists", len(rows) == 1, f"got {len(rows)}"):
        failures += 1

    # ---- 4: capacity API still reachable (carryover Ep 11) ----
    try:
        bap_tok = CRED.get_token('https://api.bap.microsoft.com/.default').token
        r = requests.get(
            'https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform'
            '/scopes/admin/environments?api-version=2020-06-01',
            headers={'Authorization': 'Bearer ' + bap_tok})
        if not check("Capacity / BAP admin API reachable", r.status_code == 200,
                     f"HTTP {r.status_code}"):
            failures += 1
    except Exception as e:
        check("Capacity / BAP admin API reachable", False, str(e)); failures += 1

    # ---- 5: teaser launch does NOT exist yet ----
    teaser_safe = TEASER.replace("'", "''")
    teaser_rows = fetch(f"/api/data/v9.2/lc_launchs?$select=lc_launchid"
                        f"&$filter=lc_name eq '{teaser_safe}'")
    if not check(f"Teaser launch '{TEASER}' does not yet exist",
                 len(teaser_rows) == 0,
                 f"got {len(teaser_rows)} -- delete before recording"):
        failures += 1

    # ---- 6: OSS readiness files at repo root ----
    for fname in ['LICENSE', 'README.md', 'CHANGELOG.md', '.env.example', '.gitignore']:
        if not check(f"OSS file present: {fname}",
                     os.path.exists(os.path.join(ROOT, fname))):
            failures += 1

    print()
    if failures == 0:
        print("ALL GREEN -- Ep 12 orchestra harness ready.")
        print()
        print("REMAINING (manual / scripts to run on the day):")
        print("  - Run setup_launch_week.py --apply (rest the env to perfect)")
        print("  - Rehearse the orchestra montage end-to-end")
        print("  - Decide whether to mutate Q3 to Launched on camera or leave it ReadyForLaunch")
        return 0
    print(f"{failures} FAILURE(S) -- fix before recording.")
    return 1


if __name__ == '__main__':
    sys.exit(main())
