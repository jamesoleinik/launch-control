"""Automate Dynamics 365 F&O data import via the DMF package REST API.

This is the supported, server-side bulk-import path. Unlike direct OData entity
writes (POST /data/Currencies), which fail in the X++ deserializer on a bare
environment, this drives the same Data management engine the browser uses:

    GetAzureWriteUrl  -> writable blob SAS URL
    PUT <package.zip> -> upload a DMF data package (Manifest.xml, PackageHeader.xml, <Entity>.csv)
    ImportFromPackage -> queue the import (returns executionId)
    GetExecutionSummaryStatus -> poll until terminal
    GetEntityExecutionSummaryStatusList / GetExecutionErrors -> per-entity result + errors

Docs: https://learn.microsoft.com/en-us/dynamics365/fin-ops-core/dev-itpro/data-entities/data-management-api

Verified end to end on eppcdemo1fno (the Ep 9 env): GetAzureWriteUrl, the blob
PUT, ImportFromPackage, and the queued batch import all succeed and the data
lands (a Currencies self-test inserts USD and the row is then readable at
GET /data/Currencies). Getting there required five things the package MUST get
right; each one silently imports zero rows or fails if wrong:

  1. Manifest schema. Use <DefinitionGroupName> + <PackageEntityList> +
     <DataManagementPackageEntityData> with an explicit <EntityMapList> (one
     <EntityMap> per column). A manifest without the field map registers no
     entity, so the import "succeeds" with zero rows and zero errors.
  2. Entity name. Use the DMF entity label (for example "Currencies", target
     CurrencyEntity), not the OData type name ("Currency"). The wrong name
     returns 400 "Entity <x> does not exist in the target environment".
  3. CSV encoding. SourceFormat CSV-Unicode requires the data file to be UTF-16
     LE with BOM. A UTF-8 file fails with entity error "Selected file is not
     Unicode".
  4. XML namespace. Manifest.xml and PackageHeader.xml must use
     http://schemas.microsoft.com/dynamics/2015/01/DataManagement.
  5. CRLF line endings. The CSV must use \r\n. An LF-only file fails
     ImportFromPackage with a misleading "the mapping is incorrect for entity
     <x> and field {GUID}" (the field GUID is random per call). build_package
     normalizes line endings so any input file works.

Note on dependencies: low-dependency reference data (for example Currencies)
imports cleanly. Master/transactional entities (Vendors, Released products,
Purchase orders) additionally require the usual F&O setup (number sequences,
item model/dimension groups, posting profiles) and will report target errors
until that configuration exists. The CSV header columns must match the DMF
entity field names (uppercase); they become both EntityField and XMLField.

Usage:
    $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
    python episodes/ep-09-dataverse-fno/dmf_package_import.py --selftest-currency
    python episodes/ep-09-dataverse-fno/dmf_package_import.py --entity Currencies --csv path\to\Currencies.csv --legal-entity dat
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

# A minimal, valid Currencies row. Header columns must match the DMF entity
# field names (uppercase); these become both EntityField and XMLField in the map.
CURRENCY_CSV = (
    "CURRENCYCODE,NAME,SYMBOL\r\n"
    "USD,US Dollar,$\r\n"
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
    if not r.ok:
        print(f"  [{action}] HTTP {r.status_code}: {r.text[:600]}")
    r.raise_for_status()
    return r.json().get("value")


def _csv_columns(csv_text):
    """First non-empty line of the CSV holds the column headers."""
    for line in csv_text.lstrip("\ufeff").splitlines():
        if line.strip():
            return [c.strip() for c in line.split(",") if c.strip()]
    return []


def _entity_map(field):
    # XMLField = column header in the CSV; EntityField = the DMF entity field.
    # We keep them identical, so the CSV header must use the entity field names.
    return (
        "<EntityMap>"
        "<ArrayIndex>0</ArrayIndex>"
        f"<EntityField>{field}</EntityField>"
        '<EntityFieldConversionList i:nil="true" />'
        "<IsAutoDefault>false</IsAutoDefault>"
        "<IsAutoGenerated>false</IsAutoGenerated>"
        "<IsDefaultValueEqualNull>false</IsDefaultValueEqualNull>"
        "<UseTextQualifier>false</UseTextQualifier>"
        f"<XMLField>{field}</XMLField>"
        "</EntityMap>"
    )


def build_manifest(group, entity_name, file_name, columns):
    """A valid DMF manifest: definition group + one entity with an explicit
    field map (EntityMapList). Without the field map DMF stages nothing."""
    maps = "".join(_entity_map(c) for c in columns)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<DataManagementPackageManifest '
        'xmlns:i="http://www.w3.org/2001/XMLSchema-instance" '
        f'xmlns="{DC_NS}">'
        f'<DefinitionGroupName>{group}</DefinitionGroupName>'
        '<Description>Launch Control DMF import</Description>'
        '<PackageEntityList>'
        '<DataManagementPackageEntityData>'
        '<DefaultRefreshType>FullPush</DefaultRefreshType>'
        '<Disable>false</Disable>'
        f'<EntityMapList>{maps}</EntityMapList>'
        f'<EntityName>{entity_name}</EntityName>'
        '<ExecutionUnit>0</ExecutionUnit>'
        f'<InputFilePath>{file_name}</InputFilePath>'
        '<LevelInExecutionUnit>0</LevelInExecutionUnit>'
        '<SequenceInLevel>0</SequenceInLevel>'
        '<SkipStaging>false</SkipStaging>'
        '<SourceFormat>CSV-Unicode</SourceFormat>'
        '</DataManagementPackageEntityData>'
        '</PackageEntityList>'
        '</DataManagementPackageManifest>'
    )


def build_header(group):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<DataManagementPackageHeader '
        'xmlns:i="http://www.w3.org/2001/XMLSchema-instance" '
        f'xmlns="{DC_NS}">'
        f'<Description>{group}</Description>'
        '<ManifestType>Microsoft.Dynamics.AX.Framework.Tools.DataManagement.'
        'Serialization.DataManagementPackageManifest</ManifestType>'
        '<PackageType>DefinitionGroup</PackageType>'
        '<PackageVersion>2</PackageVersion>'
        '</DataManagementPackageHeader>'
    )


def _normalize_newlines(text):
    # CSV-Unicode parsing requires CRLF line endings. An LF-only file mis-aligns
    # the field mapping and fails with "mapping is incorrect for entity ... field {GUID}".
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")


def build_package(group, entity_name, csv_text):
    file_name = f"{entity_name}.csv"
    csv_text = _normalize_newlines(csv_text)
    columns = _csv_columns(csv_text)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Manifest.xml", build_manifest(group, entity_name, file_name, columns))
        z.writestr("PackageHeader.xml", build_header(group))
        # CSV-Unicode requires the data file to be UTF-16 LE with BOM and CRLF lines.
        z.writestr(file_name, csv_text.encode("utf-16"))
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
            # Execution record not created yet; the batch is still starting.
            print("  status: pending (execution summary not available yet)")
            last = "Pending"
        else:
            print(f"  status poll HTTP {r.status_code}: {r.text[:160]}")
        time.sleep(10)
    return last


def entity_status_list(url, token, execution_id):
    try:
        return _post(url, token, "GetEntityExecutionSummaryStatusList",
                     {"executionId": execution_id})
    except Exception:
        return None


def execution_errors(url, token, execution_id):
    try:
        return _post(url, token, "GetExecutionErrors", {"executionId": execution_id})
    except Exception:
        return None


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
    group = f"LC-{entity_name}-{uuid.uuid4().hex[:8]}"
    print(f"F&O: {url}  | entity: {entity_name}  | legal entity: {legal_entity}")
    print(f"  definition group: {group}")
    pkg = build_package(group, entity_name, csv_text)
    unique = f"{group}.zip"
    blob_url = get_write_url(url, token, unique)
    print(f"  got write URL ({unique})")
    upload_blob(blob_url, pkg)
    print(f"  uploaded package ({len(pkg)} bytes)")
    returned = import_package(url, token, blob_url, group, legal_entity, "")
    print(f"  import queued, executionId: {returned}")
    status = poll_status(url, token, returned, timeout_s=420)
    print(f"  final status: {status}")
    per_entity = entity_status_list(url, token, returned)
    if per_entity:
        print(f"  per-entity: {per_entity}")
    if status not in ("Succeeded", "Pending", None):
        errs = execution_errors(url, token, returned)
        if errs and errs != "[]":
            print(f"  execution errors: {errs}")
        keys = pull_errors(url, token, returned, entity_name)
        if keys:
            print(f"  error keys file: {keys}")
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity")
    ap.add_argument("--csv")
    ap.add_argument("--legal-entity", default="dat")
    ap.add_argument("--selftest-currency", action="store_true")
    args = ap.parse_args()

    if args.selftest_currency:
        status = run_import("Currencies", CURRENCY_CSV, args.legal_entity)
    elif args.entity and args.csv:
        with open(args.csv, encoding="utf-8-sig") as f:
            csv_text = f.read()
        status = run_import(args.entity, csv_text, args.legal_entity)
    else:
        ap.error("provide --selftest-currency or --entity and --csv")
        return 2
    return 0 if status == "Succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
