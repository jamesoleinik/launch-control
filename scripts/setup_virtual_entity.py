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
import urllib.parse
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

    # Look up the plugin assembly by NAME (not by hard-coded GUID, since the
    # assembly id changes every time the env is rebuilt).
    print("0. Looking up plugin assembly by name...")
    flt = urllib.parse.quote("name eq 'GitHubIssuesProvider'", safe="")
    result = api_call(env_url, token, "GET",
        f"pluginassemblies?$filter={flt}&$select=pluginassemblyid")
    if not result.get("value"):
        print("  ERROR: GitHubIssuesProvider assembly not registered. "
              "Run scripts/register_ve_plugin.py first.")
        return
    assembly_id = result["value"][0]["pluginassemblyid"]
    print(f"  Assembly id: {assembly_id}")

    # Step 1: Look up the plugin types
    print("\n1. Looking up plugin types...")
    flt = urllib.parse.quote(f"_pluginassemblyid_value eq {assembly_id}", safe="")
    result = api_call(env_url, token, "GET",
        f"plugintypes?$filter={flt}&$select=plugintypeid,typename,friendlyname")
    plugin_types = result.get("value", [])
    print(f"  Found {len(plugin_types)} plugin types:")

    retrieve_multiple_id = None
    retrieve_id = None
    for pt in plugin_types:
        print(f"    {pt['typename']} ({pt['plugintypeid']})")
        if pt["typename"].endswith("RetrieveMultiplePlugin"):
            retrieve_multiple_id = pt["plugintypeid"]
        elif pt["typename"].endswith("RetrievePlugin"):
            retrieve_id = pt["plugintypeid"]

    if not retrieve_multiple_id:
        print("  ERROR: RetrieveMultiplePlugin not found. "
              "Run scripts/register_ve_plugin.py to register plugin types.")
        return

    # Step 2: Look up or create the entitydataprovider row.
    # Normal flow: PRT created this row, we just look it up.
    # If you ran scripts/python/register_ve_data_provider.py instead, same lookup.
    print("\n2. Looking up entitydataprovider row...")
    flt = urllib.parse.quote("name eq 'GitHubIssuesProvider'", safe="")
    result = api_call(env_url, token, "GET",
        f"entitydataproviders?$filter={flt}&$select=entitydataproviderid")
    if result.get("value"):
        provider_id = result["value"][0]["entitydataproviderid"]
        print(f"  Existing data provider: {provider_id}")
    else:
        print("  ERROR: no entitydataprovider row named 'GitHubIssuesProvider' found. "
              "Register one via PRT (Register -> Register New Data Provider) "
              "or run scripts/python/register_ve_data_provider.py first.")
        return

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
            # Virtual-entity required managed properties - see SETUP-GUIDE.md
            # Step 5. Omitting any of these causes 400 errors like
            # "CanChangeTrackingBeEnabled can not be active" or
            # "Cannot create charts for virtual Entity".
            "ChangeTrackingEnabled": False,
            "CanChangeTrackingBeEnabled": {"Value": False, "CanBeChanged": False},
            "IsAvailableOffline": False,
            "IsVisibleInMobileClient": {"Value": False, "CanBeChanged": False},
            "CanCreateCharts": {"Value": False, "CanBeChanged": False},
            "ExternalName": "github_issues",
            "ExternalCollectionName": "github_issues",
            "DataProviderId": provider_id,
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
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
                    "AttributeType": "Memo",
                    "SchemaName": "lc_Description",
                    "MaxLength": 100000,
                    "Format": "TextArea",
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Description", "LanguageCode": 1033}]
                    },
                    "ExternalName": "body"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
                    "AttributeType": "String",
                    "SchemaName": "lc_Labels",
                    "MaxLength": 1000,
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Labels", "LanguageCode": 1033}]
                    },
                    "ExternalName": "labels"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
                    "AttributeType": "DateTime",
                    "SchemaName": "lc_CreatedAt",
                    "Format": "DateAndTime",
                    "DateTimeBehavior": {"Value": "UserLocal"},
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Created At", "LanguageCode": 1033}]
                    },
                    "ExternalName": "created_at"
                },
                {
                    "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
                    "AttributeType": "DateTime",
                    "SchemaName": "lc_UpdatedAt",
                    "Format": "DateAndTime",
                    "DateTimeBehavior": {"Value": "UserLocal"},
                    "DisplayName": {
                        "@odata.type": "Microsoft.Dynamics.CRM.Label",
                        "LocalizedLabels": [{"@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                                             "Label": "Updated At", "LanguageCode": 1033}]
                    },
                    "ExternalName": "updated_at"
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
