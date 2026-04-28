"""Register the GitHub Issues virtual entity data provider plugin in Dataverse.

Steps:
1. Register the plugin assembly
2. Register the data provider
3. Create the virtual entity data source
4. Create the virtual table
"""

import os
import sys
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env

import urllib.request
import json


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
                # Extract entity ID from OData-EntityId header
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

    # Read the compiled DLL
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

    # Step 1: Register the plugin assembly
    print("\n1. Registering plugin assembly...")
    try:
        assembly_id = api_call(env_url, token, "POST", "pluginassemblies", {
            "name": "GitHubIssuesProvider",
            "content": dll_content,
            "isolationmode": 2,  # Sandbox
            "sourcetype": 0,     # Database
            "description": "Virtual entity data provider for GitHub Issues",
        })
        print(f"  Assembly registered: {assembly_id}")
    except Exception as e:
        if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
            print("  Assembly already exists.")
            # Look it up
            result = api_call(env_url, token, "GET",
                "pluginassemblies?$filter=name eq 'GitHubIssuesProvider'&$select=pluginassemblyid")
            assembly_id = result["value"][0]["pluginassemblyid"]
            print(f"  Existing ID: {assembly_id}")
        else:
            raise

    print("\nPlugin assembly registered successfully!")
    print(f"Assembly ID: {assembly_id}")
    print("\nNext steps (manual in Plugin Registration Tool):")
    print("  1. Register plugin steps for RetrieveMultiple and Retrieve")
    print("  2. Create virtual entity data provider")
    print("  3. Create virtual table lc_GitHubIssue")


if __name__ == "__main__":
    main()
