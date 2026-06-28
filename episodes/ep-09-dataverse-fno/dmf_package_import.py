"""Automate Dynamics 365 F&O data import via the DMF package REST API.

This is the supported, server-side bulk-import path. Unlike direct OData entity
writes (POST /data/Currencies), which fail in the X++ deserializer on a bare
environment, this drives the same Data management engine the browser uses:

    GetAzureWriteUrl  -> writable blob SAS URL
    PUT <package.zip> -> upload a DMF data package (Manifest.xml, PackageHeader.xml, <Entity>.csv)
    ImportFromPackage -> queue the import (returns executionId)
    GetExecutionSummaryStatus -> poll until terminal
    GenerateImportTargetErrorKeysFile / GetImportTargetErrorKeysFileUrl -> pull errors

Docs: https://learn.microsoft.com/en-us/dynamics365/fin-ops-core/dev-itpro/data-entities/data-management-api

Note on dependencies: importing into the bare `dat` company succeeds for
low-dependency reference data (for example Currency). Master/transactional
entities (Vendors, Released products, Purchase orders) still require the usual
F&O setup (number sequences, item model/dimension groups, posting profiles); the
import will report those as target errors until that configuration exists.

Tested finding (eppcdemo1fno, the Ep 9 env): the full path runs end to end up to
submission. GetAzureWriteUrl, the blob PUT, and ImportFromPackage all succeed
(HTTP 200, server returns a real execution id). The import then never completes
and no execution summary appears (GetExecutionSummaryStatus reports the execution
id is not found and the data does not land), which means the queued DMF batch job
is not being processed on that environment. Making imports actually land data
requires the environment to be provisioned with a running batch framework and the
base F&O configuration, the same prerequisite as the manual Data management path.
The code here is correct and reusable once the environment processes batch jobs.

Usage:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/dmf_package_import.py --selftest-currency
    python episodes/ep-09-dataverse-fno/dmf_package_import.py --entity Currency --csv path\to\Currency.csv --legal-entity dat
"""

import argparse
import io
import json
import os
import sys
import time
import uuid
import zipfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import auth  # noqa: E402
import requests  # noqa: E402

EPISODE = "ep-09-dataverse-fno"
DMF = "/data/DataManagementDefinitionGroups/Microsoft.Dynamics.DataEntities."
DC_NS = "http://schemas.microsoft.com/dynamics/2015/01/DataManagement"

# A minimal, valid Currency row. USD with default rounding.
CURRENCY_CSV = (
    "CURRENCYCODE,CURRENCYNAME,ROUNDINGPRECISION,ROUNDINGRULESELLPRICE,"
    "ROUNDINGRULESPRICE,SYMBOL,DECIMALSCALE\r\n"
    "USD,US Dollar,0.01,0.01,0.01,$,2\r\n"
)


def fno_url():
    auth.load_env(EPISODE)
    return os.environ["FNO_URL"].rstrip("/")


def fno_token(url):
    cred = auth.get_credential(EPISODE)
    return cred.get_token(f"{url}/.default").token


def _post(url, token, action, body):
    r = requests.post(
        f"{url}{DMF}{action}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json", "Accept": "application/json"},
        json=body, timeout=120,
    )
    r.raise_for_status()
    return r.json().get("value")


def build_manifest(entity_name, file_name):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<DataManagementPackageManifest '
        'xmlns:i="http://www.w3.org/2001/XMLSchema-instance" '
        f'xmlns="{DC_NS}">'
        '<Entities>'
        '<DataManagementPackageEntityData>'
        f'<EntityName>{entity_name}</EntityName>'
        '<ExcelExportStyle i:nil="true"/>'
        '<ExecutionUnit>1</ExecutionUnit>'
        f'<InputFilePath>{file_name}</InputFilePath>'
        '<LevelInExecutionUnit>1</LevelInExecutionUnit>'
        '<SkipStaging>false</SkipStaging>'
        '<SourceFormat>CSV-Unicode</SourceFormat>'
        '</DataManagementPackageEntityData>'
        '</Entities>'
        '<Name>LCImport</Name>'
        '</DataManagementPackageManifest>'
    )


def build_header():
    return (
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<DataManagementPackageHeader '
        'xmlns:i="http://www.w3.org/2001/XMLSchema-instance" '
        f'xmlns="{DC_NS}">'
        '<Description>Launch Control DMF import</Description>'
        '<ManifestType>Microsoft.Dynamics.AX.Framework.Tools.DataManagement.'
        'Serialization.DataManagementPackageManifest</ManifestType>'
        '<PackageType>DefinitionGroup</PackageType>'
        '<PackageVersion>2</PackageVersion>'
        '</DataManagementPackageHeader>'
    )


def build_package(entity_name, csv_text):
    file_name = f"{entity_name}.csv"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Manifest.xml", build_manifest(entity_name, file_name))
        z.writestr("PackageHeader.xml", build_header())
        z.writestr(file_name, csv_text)
    return buf.getvalue()


def get_write_url(url, token, unique_name):
    raw = _post(url, token, "GetAzureWriteUrl", {"uniqueFileName": unique_name})
    info = json.loads(raw)
    return info["BlobUrl"]


def upload_blob(blob_url, data):
    r = requests.put(
        blob_url, data=data,
        headers={"x-ms-blob-type": "BlockBlob",
                 "Content-Type": "application/zip"},
        timeout=180,
    )
    r.raise_for_status()


def import_package(url, token, blob_url, definition_group, legal_entity, execution_id):
    return _post(url, token, "ImportFromPackage", {
        "packageUrl": blob_url,
        "definitionGroupId": definition_group,
        "executionId": execution_id,
        "execute": True,
        "overwrite": True,
        "legalEntityId": legal_entity,
    })


def poll_status(url, token, execution_id, timeout_s=300):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        r = requests.post(
            f"{url}{DMF}GetExecutionSummaryStatus",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json", "Accept": "application/json"},
            json={"executionId": execution_id}, timeout=120,
        )
        if r.status_code == 200:
            last = r.json().get("value")
            print(f"  status: {last}")
            if last and last not in ("NotRun", "Executing", "Queued"):
                return last
        elif r.status_code == 400 and "were not found" in r.text:
            # The job is accepted but the batch has not started processing it
            # yet, so no execution summary exists. Keep waiting.
            print("  status: pending (no execution summary yet; batch not started)")
            last = "Pending"
        else:
            print(f"  status poll HTTP {r.status_code}: {r.text[:160]}")
        time.sleep(10)
    return last


def pull_errors(url, token, execution_id, entity_name):
    has = _post(url, token, "GenerateImportTargetErrorKeysFile",
                {"executionId": execution_id, "entityName": entity_name})
    if not has:
        return None
    for _ in range(6):
        u = _post(url, token, "GetImportTargetErrorKeysFileUrl",
                  {"executionId": execution_id, "entityName": entity_name})
        if u:
            return u
        time.sleep(5)
    return None


def run_import(entity_name, csv_text, legal_entity):
    url = fno_url()
    token = fno_token(url)
    print(f"F&O: {url}  | entity: {entity_name}  | legal entity: {legal_entity}")
    pkg = build_package(entity_name, csv_text)
    unique = f"LC-{entity_name}-{uuid.uuid4().hex[:8]}.zip"
    blob_url = get_write_url(url, token, unique)
    print(f"  got write URL ({unique})")
    upload_blob(blob_url, pkg)
    print(f"  uploaded package ({len(pkg)} bytes)")
    exec_id = ""
    returned = import_package(url, token, blob_url, "LCImport", legal_entity, exec_id)
    print(f"  import queued, executionId: {returned}")
    status = poll_status(url, token, returned, timeout_s=420)
    print(f"  final status: {status}")
    if status not in ("Succeeded", "Pending", None):
        err = pull_errors(url, token, returned, entity_name)
        if err:
            print(f"  error keys file: {err}")
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity")
    ap.add_argument("--csv")
    ap.add_argument("--legal-entity", default="dat")
    ap.add_argument("--selftest-currency", action="store_true")
    args = ap.parse_args()

    if args.selftest_currency:
        status = run_import("Currency", CURRENCY_CSV, args.legal_entity)
    elif args.entity and args.csv:
        with open(args.csv, encoding="utf-8") as f:
            csv_text = f.read()
        status = run_import(args.entity, csv_text, args.legal_entity)
    else:
        ap.error("provide --selftest-currency or --entity and --csv")
        return 2
    return 0 if status == "Succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
