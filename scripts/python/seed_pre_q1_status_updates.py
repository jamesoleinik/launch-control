"""Seed pre-Q1-2026 status updates so Ep 14's FetchXML cleanup demo has data to delete.

Creates ~12 lc_statusupdate rows backdated to Oct-Dec 2025 using `overriddencreatedon`,
each tagged in lc_title with a `[PRE-Q1-SEED]` prefix so teardown is trivial:

    DELETE-by-filter via FetchXML on lc_title startswith 'PreQ1Seed::'
    -- which is exactly what the dv-admin demo's FetchXML beat will do.

Idempotent: re-running checks for existing seeded rows by tag and skips creation if
>=12 already exist. Use --force to wipe and re-create.

Run: python scripts/python/seed_pre_q1_status_updates.py [--force]
"""
import os, sys, argparse, requests
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv
from auth import get_credential

load_dotenv(os.path.join(ROOT, '.env'))
URL = os.environ['DATAVERSE_URL']
TOK = get_credential().get_token(URL + '/.default').token
H = {'Authorization': 'Bearer ' + TOK, 'Accept': 'application/json',
     'Content-Type': 'application/json',
     'OData-MaxVersion': '4.0', 'OData-Version': '4.0'}

TAG = 'PreQ1Seed::'
LAUNCH_NAME = os.environ.get('LAUNCH_CONTROL_LAUNCH_NAME', 'Q3 Widget Launch')

# Backdated demo content: realistic agent voices from Eps 6-8
SEEDS = [
    ('2025-10-03T16:00:00Z', 'Sentinel: kickoff capture',
     'Initial scoping notes captured from kickoff meeting. No blockers identified.'),
    ('2025-10-15T14:30:00Z', 'Coordinator: scope alignment',
     'Marketing and engineering aligned on launch surface area. Legal review queued.'),
    ('2025-10-28T11:00:00Z', 'Sentinel: risk scan',
     'Initial risk scan complete. Three areas flagged: capacity, certs, compliance.'),
    ('2025-11-04T09:15:00Z', 'Coordinator: milestone draft',
     'Draft milestone list reviewed with PMs. 12 milestones proposed; 8 confirmed.'),
    ('2025-11-12T17:45:00Z', 'Code-first agent: backlog import',
     'Imported 28 historical tasks from Tracker A and 21 from Tracker B.'),
    ('2025-11-19T08:30:00Z', 'Sentinel: weekly digest',
     'Week 47 digest: scope still firming. No blockers escalated this week.'),
    ('2025-11-26T13:00:00Z', 'Coordinator: stakeholder sync',
     'Cross-team stakeholder sync notes captured. Marketing dependency flagged.'),
    ('2025-12-03T15:30:00Z', 'Sentinel: capacity check',
     'Capacity team confirmed initial estimates. No INC ticket yet required.'),
    ('2025-12-10T10:00:00Z', 'Code-first agent: Tracker D ingest',
     'Tracker D (Trello board) imported. 12 additional tasks linked to milestones.'),
    ('2025-12-15T18:00:00Z', 'Sentinel: pre-holiday checkpoint',
     'Pre-holiday checkpoint: all teams green. Returning Jan 5.'),
    ('2025-12-19T16:00:00Z', 'Coordinator: holiday handoff',
     'Holiday handoff complete. On-call rotation set for Dec 20-Jan 4.'),
    ('2025-12-29T09:00:00Z', 'Sentinel: year-end snapshot',
     'Year-end snapshot archived. Q1 planning kicks off Jan 6.'),
]


def fetch(path):
    out, full = [], URL + path
    while full:
        r = requests.get(full, headers=H)
        r.raise_for_status()
        j = r.json()
        out.extend(j.get('value', []))
        full = j.get('@odata.nextLink')
    return out


def find_launch():
    safe = LAUNCH_NAME.replace("'", "''")
    rows = fetch(f"/api/data/v9.2/lc_launchs?$select=lc_launchid&$filter=lc_name eq '{safe}'")
    if not rows:
        raise SystemExit(f"Launch {LAUNCH_NAME!r} not found.")
    return rows[0]['lc_launchid']


def find_existing():
    return fetch(f"/api/data/v9.2/lc_statusupdates?$select=lc_statusupdateid,lc_title"
                 f"&$filter=startswith(lc_title,'{TAG}')")


def delete(rec_id):
    r = requests.delete(URL + f"/api/data/v9.2/lc_statusupdates({rec_id})", headers=H)
    r.raise_for_status()


def create(launch_id, when_iso, title, body):
    payload = {
        'lc_title': f'{TAG}{title}',
        'lc_body': body,
        'lc_updatedon': when_iso,
        'overriddencreatedon': when_iso,
        'lc_LaunchId@odata.bind': f'/lc_launchs({launch_id})',
    }
    r = requests.post(URL + '/api/data/v9.2/lc_statusupdates', headers=H, json=payload)
    if r.status_code >= 400:
        raise SystemExit(f"Create failed ({r.status_code}): {r.text}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='wipe existing seeded rows first')
    args = ap.parse_args()

    launch_id = find_launch()
    print(f"Launch: {LAUNCH_NAME} ({launch_id})")

    existing = find_existing()
    print(f"Existing seeded rows: {len(existing)}")

    if args.force and existing:
        print(f"Deleting {len(existing)} existing seeded rows...")
        for r in existing:
            delete(r['lc_statusupdateid'])
        existing = []

    if len(existing) >= len(SEEDS):
        print(f"Already have >= {len(SEEDS)} seeded rows. Done. (Use --force to redo.)")
        return 0

    print(f"Creating {len(SEEDS)} backdated status updates...")
    for when, title, body in SEEDS:
        create(launch_id, when, title, body)
        print(f"  + {when[:10]}  {title}")

    final = find_existing()
    print(f"\nDone. Now have {len(final)} seeded rows tagged {TAG}.")
    print("Verify pre-Q1 createdon stuck:")
    for r in fetch(f"/api/data/v9.2/lc_statusupdates?$select=lc_title,createdon"
                   f"&$filter=startswith(lc_title,'{TAG}')"
                   f"&$orderby=createdon asc&$top=3"):
        print(f"  {r.get('createdon')!r:30s} {r['lc_title']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
