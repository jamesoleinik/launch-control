"""Register the GitHub Issues virtual entity data provider plugin in Dataverse.

Steps:
1. Register the plugin assembly (POST /pluginassemblies)
2. Register the two plugin types (POST /plugintypes x2) - REQUIRED for PRT to
   populate the Retrieve / RetrieveMultiple dropdowns in "Register New Data
   Provider". The Web API does NOT auto-create plugintypes when an assembly
   is uploaded; they must be POSTed explicitly with `typename` matching the
   fully-qualified C# class name.

After this script:
3. Open PRT, Register New Data Provider on the GitHubIssuesProvider assembly.
4. Create the virtual table + columns (scripts/setup_virtual_entity.py).
"""

import os
import sys
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env

import urllib.request
import urllib.parse
import json


PLUGIN_TYPES = [
    {
        "typename": "GitHubIssuesProvider.RetrieveMultiplePlugin",
        "friendlyname": "GitHubIssuesProvider.RetrieveMultiplePlugin",
        "name": "GitHubIssuesProvider.RetrieveMultiplePlugin",
        "description": "Virtual-entity RetrieveMultiple handler for GitHub Issues.",
    },
    {
        "typename": "GitHubIssuesProvider.RetrievePlugin",
        "friendlyname": "GitHubIssuesProvider.RetrievePlugin",
        "name": "GitHubIssuesProvider.RetrievePlugin",
        "description": "Virtual-entity Retrieve handler for GitHub Issues.",
    },
    {
        "typename": "GitHubIssuesProvider.TaskBlockedRulePlugin",
        "friendlyname": "GitHubIssuesProvider.TaskBlockedRulePlugin",
        "name": "GitHubIssuesProvider.TaskBlockedRulePlugin",
        "description": "Pre-Update guardrail on lc_task: when lc_blockerreason has content, force lc_taskstatus to Blocked.",
    },
    {
        "typename": "GitHubIssuesProvider.TaskUnblockedRulePlugin",
        "friendlyname": "GitHubIssuesProvider.TaskUnblockedRulePlugin",
        "name": "GitHubIssuesProvider.TaskUnblockedRulePlugin",
        "description": "Pre-Update guardrail on lc_task: when lc_blockerreason is cleared on a Blocked task, revert lc_taskstatus to InProgress.",
    },
    {
        "typename": "GitHubIssuesProvider.TaskCompletionGuardRulePlugin",
        "friendlyname": "GitHubIssuesProvider.TaskCompletionGuardRulePlugin",
        "name": "GitHubIssuesProvider.TaskCompletionGuardRulePlugin",
        "description": "Pre-Update guardrail on lc_task: refuse to mark Done while lc_blockerreason is still set.",
    },
]


def api_call(env_url, token, method, endpoint, data=None):
    """Make a Dataverse Web API call."""
    url = f"{env_url}/api/data/v9.2/{endpoint}"
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
                entity_id_header = resp.headers.get("OData-EntityId", "")
                if "(" in entity_id_header:
                    return entity_id_header.split("(")[-1].rstrip(")")
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

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dll_path = os.path.join(
        repo_root, "datamodel", "virtual-entities", "GitHubIssuesProvider",
        "GitHubIssuesProvider", "bin", "Release", "net462",
        "GitHubIssuesProvider.dll"
    )
    print(f"DLL path: {dll_path}")

    if not os.path.exists(dll_path):
        print("ERROR: DLL not found. Run 'dotnet build --configuration Release' first.")
        return

    with open(dll_path, "rb") as f:
        dll_content = base64.b64encode(f.read()).decode("ascii")

    print(f"DLL size: {len(dll_content)} bytes (base64)")

    # Step 1: Register the plugin assembly (idempotent - GET, PATCH content
    # if it exists so re-builds are picked up, otherwise POST).
    print("\n1. Registering plugin assembly...")
    flt = urllib.parse.quote("name eq 'GitHubIssuesProvider'", safe="")
    existing_asm = api_call(env_url, token, "GET",
        f"pluginassemblies?$filter={flt}&$select=pluginassemblyid")
    if existing_asm.get("value"):
        assembly_id = existing_asm["value"][0]["pluginassemblyid"]
        print(f"  Assembly already exists. ID: {assembly_id}")
        print(f"  PATCHing content with re-built DLL...")
        api_call(env_url, token, "PATCH", f"pluginassemblies({assembly_id})", {
            "content": dll_content,
        })
        print(f"  PATCHed.")
    else:
        assembly_id = api_call(env_url, token, "POST", "pluginassemblies", {
            "name": "GitHubIssuesProvider",
            "content": dll_content,
            "isolationmode": 2,  # Sandbox
            "sourcetype": 0,     # Database
            "description": "Virtual entity data provider for GitHub Issues",
        })
        print(f"  Assembly registered: {assembly_id}")

    # Step 2: Register the plugin types. PRT needs these rows to populate the
    # Retrieve / RetrieveMultiple dropdowns in the Register-New-Data-Provider
    # dialog. Without them, PRT shows "Not Implemented" and the user is stuck.
    print("\n2. Registering plugin types...")
    flt = urllib.parse.quote(f"_pluginassemblyid_value eq {assembly_id}", safe="")
    existing = api_call(env_url, token, "GET",
        f"plugintypes?$filter={flt}&$select=plugintypeid,typename")
    existing_typenames = {t["typename"] for t in existing.get("value", [])}
    print(f"  existing plugintypes on assembly: {sorted(existing_typenames) or '(none)'}")

    for pt in PLUGIN_TYPES:
        if pt["typename"] in existing_typenames:
            print(f"  - {pt['typename']}: already registered, skipping")
            continue
        body = dict(pt)
        body["pluginassemblyid@odata.bind"] = f"/pluginassemblies({assembly_id})"
        try:
            pid = api_call(env_url, token, "POST", "plugintypes", body)
            print(f"  - {pt['typename']}: registered (id={pid})")
        except urllib.error.HTTPError as e:
            print(f"  - {pt['typename']}: FAILED — see error above")
            raise

    # Verify final state
    final = api_call(env_url, token, "GET",
        f"plugintypes?$filter={flt}&$select=plugintypeid,typename")
    final_typenames = sorted(t["typename"] for t in final.get("value", []))
    print(f"\n  final plugintypes on assembly: {final_typenames}")

    print("\nDone. Assembly + plugin types registered.")
    print(f"Assembly ID: {assembly_id}")
    print("\nNext steps:")
    print("  1. Open PRT, Register -> Register New Data Provider.")
    print("     Retrieve / RetrieveMultiple dropdowns should now list the two")
    print("     GitHubIssuesProvider.* classes (no more 'Not Implemented').")
    print("  2. After PRT completes, run scripts/setup_virtual_entity.py.")


if __name__ == "__main__":
    main()
