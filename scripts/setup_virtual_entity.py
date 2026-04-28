"""Complete the virtual entity setup for GitHub Issues.

Steps:
1. Look up the registered plugin types
2. Create the virtual entity data provider
3. Create the virtual entity data source
4. Create the virtual table lc_GitHubIssue
"""

import os
import sys
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env


def api_call(env_url, token, method, endpoint, data=None, headers_extra=None):
    url = f"{env_url}/api/data/v9.2/{endpoint}"
    # Encode spaces and special chars in query string
    url = url.replace(" ", "%20")
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("MSCRM.SolutionName", "LaunchControl")
    if headers_extra:
        for k, v in headers_extra.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                eid = resp.headers.get("OData-EntityId", "")
                if "(" in eid:
                    return eid.split("(")[-1].rstrip(")")
                return None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"  HTTP {e.code}: {error_body[:500]}")
        raise


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()
    assembly_id = "f159854b-c042-f111-bec6-000d3a336093"

    # Step 1: Look up the plugin types
    print("1. Looking up plugin types...")
    result = api_call(env_url, token, "GET",
        f"plugintypes?$filter=pluginassemblyid/pluginassemblyid eq '{assembly_id}'&$select=plugintypeid,typename,friendlyname")
    plugin_types = result.get("value", [])
    print(f"  Found {len(plugin_types)} plugin types:")

    retrieve_multiple_id = None
    retrieve_id = None
    for pt in plugin_types:
        print(f"    {pt['typename']} ({pt['plugintypeid']})")
        if "RetrieveMultiple" in pt["typename"]:
            retrieve_multiple_id = pt["plugintypeid"]
        elif "Retrieve" in pt["typename"]:
            retrieve_id = pt["plugintypeid"]

    if not retrieve_multiple_id:
        print("  ERROR: RetrieveMultiplePlugin not found")
        return

    # Step 2: Create the virtual entity data provider
    print("\n2. Creating virtual entity data provider...")
    try:
        provider_id = api_call(env_url, token, "POST", "entitydataproviders", {
            "name": "GitHub Issues Provider",
            "datasourcelogicalname": "lc_githubdatasource",
            "retrievemultipleplugin@odata.bind": f"/plugintypes({retrieve_multiple_id})",
        })
        print(f"  Data provider created: {provider_id}")
    except Exception as e:
        if "duplicate" in str(e).lower() or "already" in str(e).lower():
            print("  Data provider already exists, looking it up...")
            result = api_call(env_url, token, "GET",
                "entitydataproviders?$filter=name eq 'GitHub Issues Provider'&$select=entitydataproviderid")
            provider_id = result["value"][0]["entitydataproviderid"]
            print(f"  Existing ID: {provider_id}")
        else:
            raise

    # Step 3: Create the virtual table
    print("\n3. Creating virtual table lc_GitHubIssue...")
    try:
        table_payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
            "SchemaName": "lc_GitHubIssue",
            "DisplayName": {
                "@odata.type": "Microsoft.Dynamics.CRM.Label",
                "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                     "Label": "GitHub Issue", "LanguageCode": 1033}]
            },
            "DisplayCollectionName": {
                "@odata.type": "Microsoft.Dynamics.CRM.Label",
                "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                     "Label": "GitHub Issues", "LanguageCode": 1033}]
            },
            "Description": {
                "@odata.type": "Microsoft.Dynamics.CRM.Label",
                "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                     "Label": "GitHub issues from the launch-control repo, surfaced as virtual entities",
                                     "LanguageCode": 1033}]
            },
            "OwnershipType": "OrganizationOwned",
            "TableType": "Virtual",
            "IsActivity": False,
            "HasActivities": False,
            "HasNotes": False,
            "ExternalName": "github_issues",
            "DataProviderId": {"Value": provider_id},
            "Attributes": [
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                    "AttributeType": "String",
                    "SchemaName": "lc_Name",
                    "MaxLength": 500,
                    "IsPrimaryName": True,
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Title", "LanguageCode": 1033}]
                    },
                    "ExternalName": "title"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
                    "AttributeType": "Integer",
                    "SchemaName": "lc_IssueNumber",
                    "MinValue": 0,
                    "MaxValue": 2147483647,
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Issue Number", "LanguageCode": 1033}]
                    },
                    "ExternalName": "number"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                    "AttributeType": "String",
                    "SchemaName": "lc_State",
                    "MaxLength": 50,
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "State", "LanguageCode": 1033}]
                    },
                    "ExternalName": "state"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                    "AttributeType": "String",
                    "SchemaName": "lc_Url",
                    "MaxLength": 1000,
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "URL", "LanguageCode": 1033}]
                    },
                    "ExternalName": "html_url"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                    "AttributeType": "String",
                    "SchemaName": "lc_Assignee",
                    "MaxLength": 200,
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Assignee", "LanguageCode": 1033}]
                    },
                    "ExternalName": "assignee"
                },
            ]
        }

        table_id = api_call(env_url, token, "POST", "EntityDefinitions", table_payload)
        print(f"  Virtual table created: {table_id}")
    except Exception as e:
        if "already" in str(e).lower() or "duplicate" in str(e).lower():
            print("  Virtual table already exists.")
        else:
            print(f"  Error: {e}")
            raise

    print("\n=== Virtual entity setup complete! ===")
    print("Try querying: SELECT lc_name, lc_state, lc_issuenumber FROM lc_githubissue")


if __name__ == "__main__":
    main()
