"""Create the Ep 5 test harness cloud flow programmatically.

What this builds:
  A manually-triggered Power Automate cloud flow named
  "LC - Custom Tools Test Harness" in the LaunchControl solution. It calls
  the three artifacts Episode 5 produces and composes them into one JSON
  payload so the developer (and the camera) can see them succeed side by side:

    1. lc_CalculateLaunchReadiness    (.NET Custom API - Part 1)
    2. lc_CalculateLaunchReadinessFx  (Power Fx Function - Part 2)
    3. GetLatestRelease               (Custom REST connector - Part 3a)

Why programmatic:
  The whole episode's promise is that EVERY surface in this stack can be
  produced by code. The "verify it works" step shouldn't break that. We
  POST a row into the Dataverse `workflows` table with category=5 (cloud
  flow) and a `clientdata` JSON blob containing the logic-apps definition.

Idempotent: upserts on workflowidunique-style match (we look up by name+solution).

Prereqs:
  - az login
  - The three artifacts must already be deployed:
      * lc_CalculateLaunchReadiness         (deploy_plugin.py)
      * lc_CalculateLaunchReadinessFx       (deploy_fx_function.py / deploy_fx_with_teams.py)
      * Launch Control - GitHub Releases    (register_custom_connector.py)
"""
import json, os, sys, uuid, urllib.request, urllib.parse, urllib.error
from azure.identity import AzureCliCredential

ENV = "https://org40ae6a46.crm.dynamics.com"
SOLUTION = "LaunchControl"
FLOW_NAME = "LC - Custom Tools Test Harness"
FLOW_UNIQUE = "lc_customtoolstestharness"

DV_CONNECTOR_API = "/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps"
# Look up the GitHub Releases connector slug at runtime (registered by Part 3a)
GH_CONNECTOR_DISPLAY = "Launch Control - GitHub Releases"
DEFAULT_LAUNCH = "Q3 Widget Launch"
DEFAULT_OWNER = "microsoft"
DEFAULT_REPO = "PowerPlatform-Dataverse-Client"

cred = AzureCliCredential()
DV_TOKEN = cred.get_token(f"{ENV}/.default").token
PAPI_TOKEN = cred.get_token("https://service.powerapps.com/.default").token


def dv(method, path, body=None, extra_headers=None):
    h = {"Authorization": "Bearer " + DV_TOKEN, "Accept": "application/json",
         "Content-Type": "application/json", "OData-MaxVersion": "4.0",
         "OData-Version": "4.0", "Prefer": "return=representation"}
    if extra_headers:
        h.update(extra_headers)
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            ENV + "/api/data/v9.2" + path, data=data, headers=h, method=method))
        txt = r.read().decode()
        return r.status, (json.loads(txt) if txt else None)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}")
        print(e.read().decode())
        raise


def papi(method, url):
    h = {"Authorization": "Bearer " + PAPI_TOKEN, "Accept": "application/json"}
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h, method=method))
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def find_gh_connector():
    """Return the PAPI connector name for the GitHub Releases custom connector."""
    env_id = os.environ.get("ENVIRONMENT_ID", "2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07")
    q = urllib.parse.quote(f"environment eq '{env_id}'")
    s, b = papi("GET",
                f"https://api.powerapps.com/providers/Microsoft.PowerApps/apis?api-version=2016-11-01&%24filter={q}&%24top=2000")
    if s != 200:
        return None
    for a in b.get("value", []):
        p = a.get("properties", {})
        if p.get("isCustomApi") and p.get("displayName") == GH_CONNECTOR_DISPLAY:
            return a["name"]
    return None


def get_solution_id():
    _, r = dv("GET",
              "/solutions?" + urllib.parse.urlencode({
                  "$select": "solutionid,uniquename",
                  "$filter": f"uniquename eq '{SOLUTION}'",
              }))
    return r["value"][0]["solutionid"] if r["value"] else None


def ensure_connection_reference(logical_name, display_name, connector_api_id):
    """Find or create a connectionreference. Returns the logical name."""
    _, r = dv("GET",
              "/connectionreferences?" + urllib.parse.urlencode({
                  "$select": "connectionreferencelogicalname,connectorid",
                  "$filter": f"connectionreferencelogicalname eq '{logical_name}'",
              }))
    if r["value"]:
        return logical_name
    print(f"      creating connection reference '{logical_name}' for {connector_api_id}")
    dv("POST", "/connectionreferences", {
        "connectionreferencelogicalname": logical_name,
        "connectionreferencedisplayname": display_name,
        "connectorid": connector_api_id,
    }, {"MSCRM.SolutionUniqueName": SOLUTION})
    return logical_name


def build_definition(dv_cref, gh_cref, gh_connector_id):
    """Logic-apps-style definition. gh_cref/gh_connector_id can be None for
    a partial deploy (Parts 1 + 2 only)."""
    trigger_props = {
        "LaunchName": {"type": "string", "title": "Launch name",
                        "default": DEFAULT_LAUNCH, "x-ms-content-hint": "TEXT"},
    }
    if gh_connector_id:
        trigger_props["Owner"] = {"type": "string", "title": "GitHub owner", "default": DEFAULT_OWNER}
        trigger_props["Repo"]  = {"type": "string", "title": "GitHub repo",  "default": DEFAULT_REPO}

    actions = {
        "Call_Custom_API_dotnet": {
            "type": "OpenApiConnection",
            "runAfter": {},
            "inputs": {
                "host": {
                    "connectionName": dv_cref,
                    "connectionReferenceName": dv_cref,
                    "operationId": "PerformUnboundAction",
                    "apiId": DV_CONNECTOR_API,
                },
                "parameters": {
                    "actionName": "lc_CalculateLaunchReadiness",
                    "lc_LaunchName": "@triggerBody()?['LaunchName']",
                },
            },
        },
        "Call_Power_Fx_Function": {
            "type": "OpenApiConnection",
            "runAfter": {"Call_Custom_API_dotnet": ["Succeeded"]},
            "inputs": {
                "host": {
                    "connectionName": dv_cref,
                    "connectionReferenceName": dv_cref,
                    "operationId": "PerformUnboundAction",
                    "apiId": DV_CONNECTOR_API,
                },
                "parameters": {
                    "actionName": "lc_CalculateLaunchReadinessFx",
                    "lc_LaunchName": "@triggerBody()?['LaunchName']",
                },
            },
        },
    }

    compose_inputs = {
        "launch":           "@triggerBody()?['LaunchName']",
        "dotnet_readiness": "@body('Call_Custom_API_dotnet')",
        "fx_readiness":     "@body('Call_Power_Fx_Function')",
    }
    last_step = "Call_Power_Fx_Function"

    if gh_connector_id:
        actions["Call_GitHub_Releases"] = {
            "type": "OpenApiConnection",
            "runAfter": {"Call_Power_Fx_Function": ["Succeeded"]},
            "inputs": {
                "host": {
                    "connectionName": gh_cref,
                    "connectionReferenceName": gh_cref,
                    "operationId": "GetLatestRelease",
                    "apiId": f"/providers/Microsoft.PowerApps/apis/{gh_connector_id}",
                },
                "parameters": {
                    "owner": "@triggerBody()?['Owner']",
                    "repo":  "@triggerBody()?['Repo']",
                },
            },
        }
        compose_inputs["latest_release"] = "@body('Call_GitHub_Releases')"
        last_step = "Call_GitHub_Releases"

    actions["Compose_Result"] = {
        "type": "Compose",
        "runAfter": {last_step: ["Succeeded"]},
        "inputs": compose_inputs,
    }
    actions["Respond"] = {
        "type": "Response",
        "kind": "Http",
        "runAfter": {"Compose_Result": ["Succeeded"]},
        "inputs": {"statusCode": 200, "body": "@outputs('Compose_Result')"},
    }

    return {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "$connections": {"defaultValue": {}, "type": "Object"},
            "$authentication": {"defaultValue": {}, "type": "SecureObject"},
        },
        "triggers": {
            "manual": {
                "type": "Request",
                "kind": "Button",
                "inputs": {"schema": {"type": "object", "properties": trigger_props, "required": ["LaunchName"]}},
            }
        },
        "actions": actions,
    }


def main():
    print("[1/4] Resolving GitHub Releases custom connector...")
    gh = find_gh_connector()
    if not gh:
        print(f"      Custom connector '{GH_CONNECTOR_DISPLAY}' NOT found.")
        print("      Deploying PARTIAL flow (Parts 1 + 2 only). To add Part 3a:")
        print("        1) paconn login")
        print("        2) python scripts/register_custom_connector.py connectors/github-releases-rest")
        print("        3) re-run this script to add the GetLatestRelease action")
    else:
        print(f"      connector id: {gh}")

    print("[2/4] Resolving LaunchControl solution + connection references...")
    sol_id = get_solution_id()
    if not sol_id:
        print("ERROR: LaunchControl solution not found.")
        sys.exit(1)

    dv_cref = ensure_connection_reference(
        "lc_dataverse_harness", "LC Dataverse (Test Harness)", DV_CONNECTOR_API)
    gh_cref = None
    if gh:
        gh_cref = ensure_connection_reference(
            "lc_githubreleases_harness", "LC GitHub Releases (Test Harness)",
            f"/providers/Microsoft.PowerApps/apis/{gh}")

    definition = build_definition(dv_cref, gh_cref, gh)
    connection_refs = {
        dv_cref: {"connection": {"connectionReferenceLogicalName": dv_cref},
                   "api": {"name": "shared_commondataserviceforapps"},
                   "runtimeSource": "embedded"},
    }
    if gh_cref:
        connection_refs[gh_cref] = {
            "connection": {"connectionReferenceLogicalName": gh_cref},
            "api": {"name": gh},
            "runtimeSource": "embedded",
        }

    clientdata = {
        "properties": {
            "connectionReferences": connection_refs,
            "definition": definition,
        },
        "schemaVersion": "1.0.0.0",
    }

    # Look up any existing flow by name
    print("[3/4] Checking for existing flow...")
    _, r = dv("GET",
              "/workflows?" + urllib.parse.urlencode({
                  "$select": "workflowid,name,statecode",
                  "$filter": f"name eq '{FLOW_NAME}' and category eq 5",
              }))
    existing = r["value"][0] if r["value"] else None

    payload = {
        "name": FLOW_NAME,
        "uniquename": FLOW_UNIQUE,
        "category": 5,   # Modern Flow
        "type": 1,       # Definition
        "primaryentity": "none",
        "description": "Episode 5 test harness - exercises the .NET Custom API, the Power Fx twin, and the GitHub Releases custom connector.",
        "statecode": 0,  # Draft (set to 1 to enable)
        "statuscode": 1,
        "clientdata": json.dumps(clientdata),
    }

    headers = {"MSCRM.SolutionUniqueName": SOLUTION}
    if existing:
        wid = existing["workflowid"]
        print(f"      deleting + recreating existing flow {wid} (PATCH cannot change conn-ref schema)...")
        dv("DELETE", f"/workflows({wid})")
        _, r = dv("POST", "/workflows", payload, headers)
        wid = r["workflowid"]
        print(f"      recreated workflow {wid}")
    else:
        print("[4/4] Creating new flow...")
        _, r = dv("POST", "/workflows", payload, headers)
        wid = r["workflowid"]
        print(f"      created workflow {wid}")

    env_id = os.environ.get("ENVIRONMENT_ID", "2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07")
    print()
    print("OK - Flow deployed.")
    print(f"     Open: https://make.powerautomate.com/environments/{env_id}/flows/{wid}")
    print(f"     Then: Edit -> Save -> Test -> Manually -> Run with LaunchName='{DEFAULT_LAUNCH}'")


if __name__ == "__main__":
    main()
