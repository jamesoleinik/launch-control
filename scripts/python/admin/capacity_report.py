"""Standalone Power Platform capacity report for the demo environment.

Pulls per-pool capacity (Database, File, Log, FinOps) for the configured demo env
AND a tenant-wide top-consumers view across every environment the caller can read.

This is the script the dv-admin demo in Ep 11 invokes when the user asks
"what's burning my capacity?" -- the agent calls it, parses the structured output,
and presents the headline numbers in chat.

Run: python scripts/python/admin/capacity_report.py [--tenant-top N]
"""
import os, sys, argparse, json, requests
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv
from auth import get_credential

load_dotenv(os.path.join(ROOT, '.env'))
DV_URL = os.environ['DATAVERSE_URL']
DEMO_ENV_NAME = os.environ.get('LAUNCH_CONTROL_ENV_NAME', 'Product Launch')

BAP = 'https://api.bap.microsoft.com'
API_VERSION = '2020-06-01'


def get_token():
    return get_credential().get_token('https://api.bap.microsoft.com/.default').token


def list_envs(tok):
    r = requests.get(
        f'{BAP}/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments'
        f'?api-version={API_VERSION}',
        headers={'Authorization': 'Bearer ' + tok})
    r.raise_for_status()
    return r.json().get('value', [])


def env_capacity(tok, env_id):
    r = requests.get(
        f'{BAP}/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/'
        f'{env_id}?$expand=properties.capacity&api-version={API_VERSION}',
        headers={'Authorization': 'Bearer ' + tok})
    r.raise_for_status()
    return r.json().get('properties', {}).get('capacity', [])


def fmt_mb(mb):
    if mb is None:
        return 'n/a'
    if mb >= 1024:
        return f'{mb / 1024:.2f} GB'
    return f'{mb:.2f} MB'


def pct(actual, rated):
    if not rated:
        return None
    return (actual / rated) * 100.0


def report_env(tok, env):
    name = env.get('properties', {}).get('displayName', '?')
    env_id = env['name']
    sku = env.get('properties', {}).get('environmentSku', '?')
    print(f"\n=== {name} ({sku})")
    print(f"    env_id: {env_id}")
    cap = env_capacity(tok, env_id)
    if not cap:
        print("    (no capacity data)")
        return
    print(f"    {'Pool':<18}{'Used':>14}{'Allocated':>14}{'Utilization':>14}")
    print(f"    {'-' * 18}{'-' * 14}{'-' * 14}{'-' * 14}")
    for c in cap:
        kind = c.get('capacityType', '?')
        actual = c.get('actualConsumption', 0)
        rated = c.get('ratedConsumption', 0)
        util = pct(actual, rated)
        util_s = f'{util:.1f}%' if util is not None else 'n/a'
        flag = '  <-- AT CAP' if util and util >= 95 else ''
        print(f"    {kind:<18}{fmt_mb(actual):>14}{fmt_mb(rated):>14}{util_s:>14}{flag}")
    updated = cap[0].get('updatedOn')
    if updated:
        print(f"    last refreshed: {updated}")


def tenant_top(tok, n):
    print(f"\n=== TENANT-WIDE TOP {n} CAPACITY CONSUMERS")
    envs = list_envs(tok)
    print(f"  scanning {len(envs)} environments visible to caller...")
    rows = []
    for e in envs:
        try:
            cap = env_capacity(tok, e['name'])
        except Exception:
            continue
        for c in cap:
            kind = c.get('capacityType')
            if kind in ('FinOpsDatabase', 'FinOpsFile'):
                continue
            actual = c.get('actualConsumption') or 0
            rated = c.get('ratedConsumption') or 0
            if rated <= 0:
                continue
            rows.append({
                'env': e.get('properties', {}).get('displayName', '?'),
                'sku': e.get('properties', {}).get('environmentSku', '?'),
                'pool': kind,
                'used_mb': actual,
                'rated_mb': rated,
                'util_pct': (actual / rated) * 100.0,
            })
    rows.sort(key=lambda r: r['util_pct'], reverse=True)
    print(f"  {'Env':<40}{'Pool':<14}{'Util':>8}{'Used':>14}")
    print(f"  {'-' * 40}{'-' * 14}{'-' * 8}{'-' * 14}")
    for r in rows[:n]:
        env_display = (r['env'][:37] + '...') if len(r['env']) > 40 else r['env']
        print(f"  {env_display:<40}{r['pool']:<14}{r['util_pct']:>7.1f}%{fmt_mb(r['used_mb']):>14}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tenant-top', type=int, default=0,
                    help='also print top-N capacity consumers across the tenant')
    ap.add_argument('--json', action='store_true',
                    help='emit machine-readable JSON instead of pretty text')
    args = ap.parse_args()

    tok = get_token()
    envs = list_envs(tok)
    target = next((e for e in envs
                   if e.get('properties', {}).get('displayName') == DEMO_ENV_NAME), None)
    if not target:
        print(f"ERROR: env {DEMO_ENV_NAME!r} not found in tenant list "
              f"({len(envs)} envs visible).")
        return 2

    if args.json:
        cap = env_capacity(tok, target['name'])
        out = {
            'env': DEMO_ENV_NAME,
            'env_id': target['name'],
            'capacity': cap,
            'fetched_at': datetime.utcnow().isoformat() + 'Z',
        }
        print(json.dumps(out, indent=2))
        return 0

    report_env(tok, target)
    if args.tenant_top:
        tenant_top(tok, args.tenant_top)
    return 0


if __name__ == '__main__':
    sys.exit(main())
