"""Shared helpers + status-code enums for Ep 15 orchestra scripts."""
from __future__ import annotations
import os, sys
from typing import Iterable

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from dotenv import load_dotenv  # noqa: E402
from auth import get_credential  # noqa: E402

LAUNCH_STATUS = {
    'Planning': 10600001, 'InProgress': 10600002, 'ReadyForLaunch': 10600003,
    'Launched': 10600004, 'OnHold': 10600005,
}
MILESTONE_STATUS = {
    'NotStarted': 10600010, 'InProgress': 10600011, 'Complete': 10600012,
    'AtRisk': 10600013, 'Blocked': 10600014,
}
TASK_STATUS = {
    'NotStarted': 10600020, 'InProgress': 10600021, 'Done': 10600022,
    'Blocked': 10600023,
}


class DV:
    """Tiny Dataverse client. Honors --dry-run by routing writes through self.dry_log."""
    def __init__(self, dry_run: bool):
        load_dotenv(os.path.join(ROOT, '.env'))
        self.url = os.environ['DATAVERSE_URL']
        self.tok = get_credential().get_token(self.url + '/.default').token
        self.h = {'Authorization': 'Bearer ' + self.tok, 'Accept': 'application/json',
                  'Content-Type': 'application/json',
                  'OData-MaxVersion': '4.0', 'OData-Version': '4.0'}
        self.dry_run = dry_run
        self.dry_log: list[str] = []

    def get(self, path: str) -> list[dict]:
        out, full = [], self.url + path
        while full:
            r = requests.get(full, headers=self.h); r.raise_for_status()
            j = r.json(); out += j.get('value', [])
            full = j.get('@odata.nextLink')
        return out

    def patch(self, path: str, body: dict, label: str = '') -> None:
        if self.dry_run:
            self.dry_log.append(f"PATCH {path}  {body}  ({label})")
            return
        r = requests.patch(self.url + path, headers=self.h, json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"PATCH {path} failed: {r.status_code} {r.text[:200]}")

    def post(self, path: str, body: dict, label: str = '') -> str | None:
        if self.dry_run:
            self.dry_log.append(f"POST  {path}  {body}  ({label})")
            return None
        r = requests.post(self.url + path, headers={**self.h, 'Prefer': 'return=representation'},
                          json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} failed: {r.status_code} {r.text[:200]}")
        return r.json().get('@odata.id')

    def delete(self, path: str, label: str = '') -> None:
        if self.dry_run:
            self.dry_log.append(f"DELETE {path}  ({label})")
            return
        r = requests.delete(self.url + path, headers=self.h)
        if r.status_code >= 400 and r.status_code != 404:
            raise RuntimeError(f"DELETE {path} failed: {r.status_code} {r.text[:200]}")

    def find_launch(self, name: str) -> dict:
        safe = name.replace("'", "''")
        rows = self.get(f"/api/data/v9.2/lc_launchs"
                        f"?$select=lc_launchid,lc_name,lc_launchstatus,statecode,statuscode"
                        f"&$filter=lc_name eq '{safe}'")
        if not rows:
            raise RuntimeError(f"Launch not found: {name}")
        if len(rows) > 1:
            raise RuntimeError(f"Multiple launches named: {name}")
        return rows[0]

    def milestones(self, launch_id: str) -> list[dict]:
        all_ms = self.get("/api/data/v9.2/lc_milestones"
                          "?$select=lc_milestoneid,lc_name,lc_milestonestatus,_lc_launchid_value")
        return [m for m in all_ms
                if (m.get('_lc_launchid_value') or '').lower() == launch_id.lower()]

    def tasks_for_milestones(self, milestone_ids: Iterable[str]) -> list[dict]:
        ids = {m.lower() for m in milestone_ids}
        all_t = self.get("/api/data/v9.2/lc_tasks"
                         "?$select=lc_taskid,lc_title,lc_taskstatus,lc_isblocked,"
                         "lc_blockerreason,_lc_milestoneid_value")
        return [t for t in all_t
                if (t.get('_lc_milestoneid_value') or '').lower() in ids]

    def flush_dry_log(self) -> None:
        if not self.dry_run:
            return
        print(f"\n[DRY RUN] {len(self.dry_log)} mutations would have been applied:")
        for line in self.dry_log[:80]:
            print(f"  {line}")
        if len(self.dry_log) > 80:
            print(f"  ... +{len(self.dry_log) - 80} more")
