"""Register the CalculateLaunchReadiness plugin and custom action in Dataverse.

Steps:
1. Register the plugin assembly
2. Register the plugin type
3. Create the custom action (custom API) message
4. Register the plugin step on the custom action
"""

import os
import sys
import base64
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env


def api(env_url, token, method, endpoint, data=None):
    url = f"{env_url}/api/data/v9.2/{endpoint}".replace(" ", "%20")
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("MSCRM.SolutionName", "LaunchControl")
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                eid = resp.headers.get("OData-EntityId", "")
                return eid.split("(")[-1].rstrip(")") if "(" in eid else None
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if any(x in body.lower() for x in ["duplicate", "already exists", "already being used", "matching key", "must be unique", "are not allowed", "violates a database constraint", "violates the database constraint"]):
            return "EXISTS"
        print(f"  HTTP {e.code}: {body[:400]}")
        raise


def main():
    load_env()
    env_url = os.environ["DATAVERSE_URL"].rstrip("/")
    token = get_token()

    # Read the DLL
    dll_path = os.path.join(
        os.path.dirname(__file__), "..",
        "plugins", "CalculateLaunchReadiness", "CalculateLaunchReadiness",
        "bin", "Release", "net462", "CalculateLaunchReadiness.dll"
    )
    dll_path = os.path.abspath(dll_path)
    print(f"DLL: {dll_path}")
    with open(dll_path, "rb") as f:
        dll_b64 = base64.b64encode(f.read()).decode("ascii")

    # Step 1: Register assembly
    print("\n1. Registering plugin assembly...")
    result = api(env_url, token, "POST", "pluginassemblies", {
        "name": "CalculateLaunchReadiness",
        "content": dll_b64,
        "isolationmode": 2,
        "sourcetype": 0,
        "description": "Custom action: CalculateLaunchReadiness for Launch Control",
    })
    if result == "EXISTS":
        print("  Assembly already exists, looking up ID and updating content...")
        r = api(env_url, token, "GET",
            "pluginassemblies?$filter=name%20eq%20'CalculateLaunchReadiness'&$select=pluginassemblyid")
        assembly_id = r["value"][0]["pluginassemblyid"]
        # PATCH the new DLL bytes onto the existing assembly so code changes deploy.
        api(env_url, token, "PATCH", f"pluginassemblies({assembly_id})", {
            "content": dll_b64,
        })
        print("  Assembly content updated.")
    else:
        assembly_id = result
    print(f"  Assembly ID: {assembly_id}")

    # Step 2: Register plugin type
    print("\n2. Registering plugin type...")
    result = api(env_url, token, "POST", "plugintypes", {
        "typename": "CalculateLaunchReadiness.CalculateLaunchReadinessPlugin",
        "friendlyname": "CalculateLaunchReadiness",
        "name": "CalculateLaunchReadiness.CalculateLaunchReadinessPlugin",
        "pluginassemblyid@odata.bind": f"/pluginassemblies({assembly_id})",
    })
    if result == "EXISTS":
        print("  Plugin type already exists, looking up ID...")
        r = api(env_url, token, "GET",
            "plugintypes?$filter=typename%20eq%20'CalculateLaunchReadiness.CalculateLaunchReadinessPlugin'&$select=plugintypeid")
        type_id = r["value"][0]["plugintypeid"]
    else:
        type_id = result
    print(f"  Plugin Type ID: {type_id}")

    # Step 3: Create Custom API (custom action)
    print("\n3. Creating Custom API (lc_CalculateLaunchReadiness)...")
    result = api(env_url, token, "POST", "customapis", {
        "uniquename": "lc_CalculateLaunchReadiness",
        "name": "lc_CalculateLaunchReadiness",
        "displayname": "Calculate Launch Readiness",
        "description": "Evaluates all 4 launch gates and returns a readiness score, summary, and verdict",
        "bindingtype": 0,  # Global (unbound)
        "boundentitylogicalname": None,
        "isfunction": False,
        "isprivate": False,
        "allowedcustomprocessingsteptype": 0,  # None (sync only)
        "executeprivilegename": None,
        "PluginTypeId@odata.bind": f"/plugintypes({type_id})",
    })
    if result == "EXISTS":
        print("  Custom API already exists, looking up ID...")
        r = api(env_url, token, "GET",
            "customapis?$filter=uniquename%20eq%20'lc_CalculateLaunchReadiness'&$select=customapiid")
        api_id = r["value"][0]["customapiid"]
    else:
        api_id = result
    print(f"  Custom API ID: {api_id}")

    # Step 4: Create request parameters
    print("\n4. Creating request parameter (lc_LaunchName)...")
    result = api(env_url, token, "POST", "customapirequestparameters", {
        "uniquename": "lc_LaunchName",
        "name": "lc_LaunchName",
        "displayname": "Launch Name",
        "description": "Name of the launch to evaluate",
        "type": 10,  # String
        "isoptional": False,
        "logicalentityname": None,
        "CustomAPIId@odata.bind": f"/customapis({api_id})",
    })
    print(f"  Request param: {result}")

    # Step 5: Create response properties
    print("\n5. Creating response properties...")
    responses = [
        ("lc_ReadinessScore", "Readiness Score", "Overall score 0-100", 2),  # Integer
        ("lc_ReadinessSummary", "Readiness Summary", "Gate-by-gate breakdown", 10),  # String
        ("lc_Verdict", "Verdict", "GO, NO-GO, or CONDITIONAL", 10),  # String
    ]
    for uname, dname, desc, ptype in responses:
        result = api(env_url, token, "POST", "customapiresponseproperties", {
            "uniquename": uname,
            "name": uname,
            "displayname": dname,
            "description": desc,
            "type": ptype,
            "logicalentityname": None,
            "CustomAPIId@odata.bind": f"/customapis({api_id})",
        })
        print(f"  Response prop {uname}: {result}")

    print("\n=== Custom Action Registered! ===")
    print(f"Call it: POST {env_url}/api/data/v9.2/lc_CalculateLaunchReadiness")
    print('Body: {{"lc_LaunchName": "Q3 Widget Launch"}}')

    # Step 6: Ensure CustomAPI is in the LaunchControl solution.
    # MSCRM.SolutionName header adds it on initial create, but if the API was
    # created before that header was set (or was created in a different solution
    # context), we need to add it explicitly. AddRequiredComponents=True pulls
    # in request params + response properties automatically.
    print("\n6. Ensuring solution membership (LaunchControl)...")
    try:
        api(env_url, token, "POST", "AddSolutionComponent", {
            "ComponentId": api_id,
            "ComponentType": 10038,  # CustomAPI
            "SolutionUniqueName": "LaunchControl",
            "AddRequiredComponents": True,
            "IncludedComponentSettingsValues": None,
        })
        print("  CustomAPI + dependencies added to LaunchControl.")
    except Exception as e:
        print(f"  (already in solution or error: {e})")


if __name__ == "__main__":
    main()
