"""Reset the Episode 9 clean-pass Dataverse state.

This script resets the Dataverse task used by the Fabrikam clean-pass demo so the
agent can mark the work complete again. It is intentionally limited to
Dataverse. It does not mutate Finance and Operations.

Finance and Operations note:
PO-10514 is a posted transaction after the demo agent posts the product receipt
and vendor invoice. Restoring that exact purchase order to confirmed, not
received, and not invoiced is a finance reversal exercise, not a safe demo reset.
The recommended path is to have an F&O owner reverse the posted vendor invoice
and product receipt through the standard F&O forms, validating accounting impact
and period status first, then confirm the remaining PO line is 22000. If that is
not practical, stage a fresh confirmed purchase order for Fabrikam with a 22000
line and update only the owned Episode 9 references that point the demo to the PO
number: Dataverse lc_vendorwork seed data, agent prompts/config, invoice fixture
metadata, and any eval rows. Do not edit those shared assets from this reset
script.

Run:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/scripts/reset_demo.py --dry-run
    python episodes/ep-09-dataverse-fno/scripts/reset_demo.py --confirm
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
TASK_ID = "c94a5e4e-f972-f111-ab0f-7ced8d6eb457"
TASK_TITLE = "Hero copy + visuals"
IN_PROGRESS = 10600302
POSTING_KEYWORDS = ("invoice", "voucher", "receipt", "posted")


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": "Bearer " + token,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }


def _managed_bool(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("Value"))
    return bool(value)


def _task_metadata(base: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    url = (
        base
        + "/EntityDefinitions(LogicalName='lc_task')/Attributes"
        + "?$select=LogicalName,AttributeType,IsValidForUpdate"
    )
    resp = requests.get(url, headers=headers, timeout=120)
    resp.raise_for_status()
    attrs = resp.json().get("value", [])
    return [
        attr
        for attr in attrs
        if any(k in attr.get("LogicalName", "").lower() for k in POSTING_KEYWORDS)
    ]


def _get_task(
    base: str, headers: dict[str, str], posting_columns: list[str]
) -> dict[str, Any]:
    columns = ["lc_title", "lc_taskstatus", "lc_taskid"] + posting_columns
    url = f"{base}/lc_tasks({TASK_ID})?$select={','.join(columns)}"
    resp = requests.get(url, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _display_value(value: Any) -> str:
    return "<null>" if value is None else str(value)


def reset_task(dry_run: bool) -> int:
    auth.load_env(EPISODE)
    base = os.environ["DATAVERSE_URL"].rstrip("/") + "/api/data/v9.2"
    headers = _headers(auth.get_token(EPISODE))

    matching_attrs = _task_metadata(base, headers)
    posting_columns = [a["LogicalName"] for a in matching_attrs]
    writable = {
        a["LogicalName"]
        for a in matching_attrs
        if _managed_bool(a.get("IsValidForUpdate"))
    }
    task = _get_task(base, headers, posting_columns)

    print(f"Dataverse env: {os.environ['DATAVERSE_URL'].rstrip('/')}")
    print(f"Task: {task.get('lc_title')} ({task.get('lc_taskid')})")
    print(f"Current status: {task.get('lc_taskstatus')}")
    if posting_columns:
        print("Posting-like columns:")
        for col in posting_columns:
            marker = "writable" if col in writable else "read-only"
            print(f"  {col}: {_display_value(task.get(col))} ({marker})")
    else:
        print("Posting-like columns: none found on lc_task")

    patch: dict[str, Any] = {}
    if task.get("lc_taskstatus") != IN_PROGRESS:
        patch["lc_taskstatus"] = IN_PROGRESS
    for col in posting_columns:
        if col in writable and task.get(col) is not None:
            patch[col] = None

    if not patch:
        print("No changes needed.")
        return 0

    print("Planned patch:")
    for key, value in patch.items():
        print(f"  {key} = {_display_value(value)}")
    if dry_run:
        print("Dry run only. No Dataverse changes were made.")
        return 0

    resp = requests.patch(
        f"{base}/lc_tasks({TASK_ID})", headers=headers, json=patch, timeout=120
    )
    resp.raise_for_status()
    verify = _get_task(base, headers, posting_columns)
    print("Applied. Verified state:")
    print(f"  lc_taskstatus = {verify.get('lc_taskstatus')}")
    for col in posting_columns:
        print(f"  {col} = {_display_value(verify.get(col))}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="preview without writing")
    mode.add_argument("--confirm", action="store_true", help="apply the reset")
    args = parser.parse_args()
    return reset_task(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
