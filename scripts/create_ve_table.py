"""Create the lc_GitHubIssue virtual table via Web API."""
import os, sys, json, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env

load_env()
env_url = os.environ["DATAVERSE_URL"].rstrip("/")
token = get_token()

# PRT-created provider with data source
provider_id = "ba26bc4e-c842-f111-bec6-000d3a336d63"

def label(text):
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [{
            "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
            "Label": text,
            "LanguageCode": 1033
        }]
    }

def managed_prop(val):
    return {"Value": val, "CanBeChanged": False}

payload = {
    "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
    "SchemaName": "lc_GitHubIssue",
    "DisplayName": label("GitHub Issue"),
    "DisplayCollectionName": label("GitHub Issues"),
    "Description": label("GitHub issues from jamesoleinik/launch-control"),
    "OwnershipType": "OrganizationOwned",
    "TableType": "Virtual",
    "IsActivity": False,
    "HasActivities": False,
    "HasNotes": False,
    "ChangeTrackingEnabled": False,
    "CanChangeTrackingBeEnabled": managed_prop(False),
    "IsAvailableOffline": False,
    "IsVisibleInMobileClient": managed_prop(False),
    "CanCreateCharts": managed_prop(False),
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
            "ExternalName": "title",
            "DisplayName": label("Title"),
        },
    ]
}

url = env_url + "/api/data/v9.2/EntityDefinitions"
data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, method="POST")
req.add_header("Authorization", "Bearer " + token)
req.add_header("Content-Type", "application/json; charset=utf-8")
req.add_header("Accept", "application/json")
req.add_header("OData-MaxVersion", "4.0")
req.add_header("OData-Version", "4.0")
req.add_header("MSCRM.SolutionName", "LaunchControl")

try:
    with urllib.request.urlopen(req) as resp:
        eid = resp.headers.get("OData-EntityId", "")
        table_id = eid.split("(")[-1].rstrip(")") if "(" in eid else "unknown"
        print("Virtual table created: %s" % table_id)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print("Error %s: %s" % (e.code, body[:500]))
