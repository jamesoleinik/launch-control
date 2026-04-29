"""One-time: add lc_StagingSource (string, 100) to lc_task and lc_milestone.

Used by Ep 3 promotion script as the upsert key + provenance back-reference.
Idempotent — re-running on a table where the column already exists prints a notice.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.auth import get_token, load_env  # noqa: E402


def main() -> int:
    load_env()
    url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "MSCRM.SolutionUniqueName": "LaunchControl",
    }
    body = {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "AttributeType": "String",
        "AttributeTypeName": {"Value": "StringType"},
        "SchemaName": "lc_StagingSource",
        "MaxLength": 100,
        "FormatName": {"Value": "Text"},
        "RequiredLevel": {"Value": "None"},
        "DisplayName": {
            "LocalizedLabels": [{"Label": "Staging Source", "LanguageCode": 1033}]
        },
        "Description": {
            "LocalizedLabels": [
                {
                    "Label": "Back-reference to staging row in format '<table>:<source_row_id>'.",
                    "LanguageCode": 1033,
                }
            ]
        },
    }
    rc = 0
    for table in ("lc_task", "lc_milestone"):
        endpoint = f"{url}/api/data/v9.2/EntityDefinitions(LogicalName='{table}')/Attributes"
        resp = requests.post(endpoint, headers=headers, data=json.dumps(body))
        if resp.status_code in (204, 201):
            print(f"  {table}: lc_StagingSource added")
        elif resp.status_code == 400 and "already exists" in resp.text.lower():
            print(f"  {table}: lc_StagingSource already exists, skipping")
        elif resp.status_code == 412 or "already" in resp.text.lower() or "duplicate" in resp.text.lower():
            print(f"  {table}: lc_StagingSource already exists, skipping")
        else:
            print(f"  {table}: HTTP {resp.status_code} {resp.text[:400]}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
