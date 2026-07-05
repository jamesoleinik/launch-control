"""Native F&O batch job (no dev box): recurring DMF export of procurement data.

Where the X++ scaffold in ``fno-batch/`` needs a developer environment to deploy,
this path stands up a genuine Finance and Operations batch job against a running
environment using only the Data management (DMF) REST API. Every run executes in
the F&O batch framework, so it shows up under Data management job history and its
tasks under System administration > Inquiries > Batch jobs.

It builds (idempotently) a DMF **export** data project for the procurement entity
the launch-procurement digest cares about, then triggers ``ExportToPackage``,
which the F&O batch server runs:

    DataManagementDefinitionGroups            (create the export project)
    DataManagementDefinitionGroupDetails      (add the entity to export)
    ExportToPackage                           (queue the export as a batch)
    GetExecutionSummaryStatus                 (poll to terminal state)
    GetExportedPackageUrl                     (SAS URL of the produced package)

Verified against the Ep 9 F&O environment: the project + entity create with 201,
ExportToPackage returns an executionId, and the execution reports ``Executing``
then a terminal status in the batch framework.

Recurrence: there are two supported ways to make this recur, both documented in
``MCP-DEMO.md`` under "Native F&O batch job":
  1. F&O-native: open the project in Data management and use "Manage recurring
     data jobs" (needs an Azure AD integration app registered in F&O).
  2. External scheduler: call this script with ``--run`` on a cron (GitHub Actions
     or Task Scheduler). Each invocation queues a fresh F&O batch, so every run
     still appears in Batch job history. This mirrors how
     ``batch_launch_sync.py`` is scheduled.

Usage:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/fno_batch_export.py --setup   # create project only
    python episodes/ep-09-dataverse-fno/fno_batch_export.py --run     # setup + run the batch export
    python episodes/ep-09-dataverse-fno/fno_batch_export.py --cleanup # remove the project
"""

import argparse
import os
import sys
import time
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
DMF = "/data/DataManagementDefinitionGroups/Microsoft.Dynamics.DataEntities."

PROJECT = "LC-Export-Procurement"
ENTITY = "Purchase order headers V2"
LEGAL_ENTITY = "dat"


def _client():
    auth.load_env(EPISODE)
    url = os.environ["FNO_URL"].rstrip("/")
    token = auth.get_credential(EPISODE).get_token(f"{url}/.default").token
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    return url, headers


def _post(url, headers, action, body):
    r = requests.post(f"{url}{DMF}{action}", headers=headers, json=body, timeout=180)
    if not r.ok:
        raise RuntimeError(f"{action} -> HTTP {r.status_code}: {r.text[:400]}")
    return r.json().get("value")


def ensure_project(url, headers):
    """Create the export data project and add the procurement entity. Both calls
    are idempotent: an existing project or entity returns a benign conflict that
    we treat as success."""
    proj = requests.post(
        f"{url}/data/DataManagementDefinitionGroups", headers=headers,
        json={
            "Name": PROJECT, "OperationType": "Export", "ProjectCategory": "Project",
            "Description": "Launch Control procurement export", "GenerateDataPackage": "No",
        }, timeout=120,
    )
    if proj.status_code == 201:
        print(f"  created export project '{PROJECT}'")
    elif proj.status_code in (400, 409) and "already exists" in proj.text.lower():
        print(f"  export project '{PROJECT}' already exists")
    elif proj.ok:
        print(f"  export project '{PROJECT}' ready")
    else:
        # A duplicate key surfaces as a 4xx we can safely ignore; anything else fails.
        if proj.status_code not in (400, 409):
            raise RuntimeError(f"create project -> HTTP {proj.status_code}: {proj.text[:400]}")
        print(f"  export project '{PROJECT}' already present")

    ent = requests.post(
        f"{url}/data/DataManagementDefinitionGroupDetails", headers=headers,
        json={
            "DefinitionGroupId": PROJECT, "EntityName": ENTITY,
            "SourceFormat": "CSV-Unicode", "ExecutionUnit": 1,
            "LevelInExecutionUnit": 1, "SequenceInLevel": 1,
            "DefaultRefreshType": "FullPush",
        }, timeout=120,
    )
    if ent.status_code == 201:
        print(f"  added entity '{ENTITY}' to the project")
    elif ent.status_code in (400, 409):
        print(f"  entity '{ENTITY}' already in the project")
    elif ent.ok:
        print(f"  entity '{ENTITY}' ready")
    else:
        raise RuntimeError(f"add entity -> HTTP {ent.status_code}: {ent.text[:400]}")


def run_export(url, headers, timeout_s=600):
    """Queue the export as an F&O batch and poll to a terminal status."""
    execution_id = f"LC-Export-{uuid.uuid4().hex[:8]}"
    returned = _post(url, headers, "ExportToPackage", {
        "definitionGroupId": PROJECT, "packageName": "LC-Procurement-Export",
        "executionId": execution_id, "reExecute": False, "legalEntityId": LEGAL_ENTITY,
    })
    execution_id = returned or execution_id
    print(f"  export queued in the F&O batch framework, executionId: {execution_id}")

    deadline = time.time() + timeout_s
    status = None
    while time.time() < deadline:
        status = _post(url, headers, "GetExecutionSummaryStatus", {"executionId": execution_id})
        print(f"  status: {status}")
        if status and status not in ("NotRun", "Executing", "Queued"):
            break
        time.sleep(15)

    if status == "Succeeded":
        pkg = _post(url, headers, "GetExportedPackageUrl", {"executionId": execution_id})
        if pkg:
            print("  exported package is ready (SAS URL retrieved)")
    return status


def cleanup(url, headers):
    r = requests.delete(
        f"{url}/data/DataManagementDefinitionGroups(Name='{PROJECT}',OperationType=Microsoft.Dynamics.DataEntities.DMFOperationType'Export')",
        headers=headers, timeout=120,
    )
    print(f"  delete project -> HTTP {r.status_code}")
    return r.ok


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--setup", action="store_true", help="create the export project and entity only")
    ap.add_argument("--run", action="store_true", help="create if needed, then run the batch export")
    ap.add_argument("--cleanup", action="store_true", help="delete the export project")
    args = ap.parse_args()

    url, headers = _client()
    print(f"F&O: {url}  | project: {PROJECT}  | entity: {ENTITY}  | legal entity: {LEGAL_ENTITY}")

    if args.cleanup:
        return 0 if cleanup(url, headers) else 1

    ensure_project(url, headers)
    if args.run:
        status = run_export(url, headers)
        print(f"\nFinal batch status: {status}")
        return 0 if status in ("Succeeded", "Executing", "Queued") else 1
    if not args.setup:
        print("\nNothing to run. Pass --setup, --run, or --cleanup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
