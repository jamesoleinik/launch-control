"""Register a custom connector in the target environment, programmatically.

Works for BOTH:
  - Plain REST connectors (e.g. connectors/github-releases-rest)
  - Remote MCP servers (the x-ms-agentic-protocol extension in the swagger
    is what makes them MCP)

Reverse-engineered from paconn's upsert.py + powerappsrp.py. Talks directly
to api.powerapps.com so the only auth dependency is `az login` -- no
separate `paconn login`, no device-code interruption.

Flow:
  1. POST /providers/Microsoft.PowerApps/apis?$filter=environment eq '<id>'
     Body: { properties: { swagger, backendService, environment, ... } }
     Returns the new connector record with a generated 'name' (slug).
  2. PATCH the same path with the slug for updates.

Idempotency:
  - If <folder>/.connector-id exists, PATCH that connector
  - Else search PAPI for a custom connector with the same displayName
  - Else POST a new one and cache its id in <folder>/.connector-id

Usage:
  python scripts/register_custom_connector.py <folder>

Env:
  ENVIRONMENT_ID -- defaults to LaunchControl 2.0
"""
import json, os, sys, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from azure.identity import AzureCliCredential

ENV_ID = os.environ.get("ENVIRONMENT_ID", "2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07")
API_VER = "2016-11-01"
PAPI = "https://api.powerapps.com"


def _req(token, method, url, body=None):
    h = {"Authorization": "Bearer " + token, "Accept": "application/json",
         "Content-Type": "application/json", "x-ms-origin": "paconn-cli"}
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method))
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _filter_query():
    return urllib.parse.quote(f"environment eq '{ENV_ID}'")


def _find_existing(papi_token, display_name):
    s, b = _req(papi_token, "GET",
                f"{PAPI}/providers/Microsoft.PowerApps/apis?api-version={API_VER}&%24filter={_filter_query()}&%24top=2000")
    if s != 200:
        return None
    for a in json.loads(b).get("value", []):
        p = a.get("properties", {})
        if p.get("isCustomApi") and p.get("displayName") == display_name:
            return a["name"]
    return None


def _backend_url(swagger):
    scheme = (swagger.get("schemes") or ["https"])[0]
    host = swagger.get("host", "")
    base = swagger.get("basePath", "/")
    return f"{scheme}://{host}{base}"


def register(folder):
    folder = Path(folder).resolve()
    swagger = json.loads((folder / "apiDefinition.swagger.json").read_text())
    api_props = json.loads((folder / "apiProperties.json").read_text())

    title = swagger["info"]["title"]
    description = swagger.get("info", {}).get("description", "")

    cred = AzureCliCredential()
    papi_token = cred.get_token("https://service.powerapps.com/.default").token

    cached = folder / ".connector-id"
    existing_id = cached.read_text().strip() if cached.exists() else _find_existing(papi_token, title)

    properties = dict(api_props.get("properties", {}))
    properties["openApiDefinition"] = swagger
    properties["backendService"] = {"serviceUrl": _backend_url(swagger)}
    properties["environment"] = {"name": ENV_ID}
    properties["description"] = description
    properties["scriptOperations"] = properties.get("scriptOperations", [])
    if not existing_id:
        properties["displayName"] = title

    payload = {"properties": properties}

    if existing_id:
        print(f"[update] PATCH {existing_id}")
        url = f"{PAPI}/providers/Microsoft.PowerApps/apis/{existing_id}?api-version={API_VER}&%24filter={_filter_query()}"
        s, b = _req(papi_token, "PATCH", url, payload)
    else:
        print(f"[create] POST /apis  (env {ENV_ID})")
        url = f"{PAPI}/providers/Microsoft.PowerApps/apis?api-version={API_VER}&%24filter={_filter_query()}"
        s, b = _req(papi_token, "POST", url, payload)

    if s not in (200, 201):
        print(f"FAIL HTTP {s}")
        print(b[:3000])
        sys.exit(1)

    resp = json.loads(b)
    connector_id = resp.get("name") or existing_id
    cached.write_text(connector_id)
    print(f"[ok] Connector id: {connector_id}")
    print(f"     displayName : {resp.get('properties', {}).get('displayName', title)}")
    print(f"     Maker UI    : https://make.powerapps.com/environments/{ENV_ID}/customconnectors")
    return connector_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: register_custom_connector.py <connector-folder>")
        sys.exit(2)
    register(sys.argv[1])
