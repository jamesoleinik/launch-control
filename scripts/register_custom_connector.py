"""Register a custom connector directly via the Dataverse Web API.

What this does
--------------
Reads a Swagger 2.0 folder under connectors/<folder>/ and POSTs (or PATCHes)
a row into the Dataverse `connector` entity inside the LaunchControl
solution. No paconn. No PAPI. No maker-portal clicks. The only auth
dependency is `az login` against the target tenant.

Works for any swagger folder under connectors/:
  * Plain REST connectors (e.g. github-releases-rest)
  * Remote MCP servers (the same `connector` entity stores the
    swagger verbatim, including `x-ms-agentic-protocol`)

Folder shape (matches what paconn expects, so existing folders work):
  connectors/<folder>/apiDefinition.swagger.json
  connectors/<folder>/apiProperties.json
  connectors/<folder>/.connector-id     (written on first run, used on re-runs)

Why Dataverse Web API instead of PAPI
-------------------------------------
PAPI (api.powerapps.com) creates connectors that live at the Power Apps
tenant layer — they show up as `shared_*` and are NOT solution-aware,
so AddSolutionComponent can't pull them into LaunchControl. The
Dataverse `connector` entity IS solution-aware: POSTing with the
`MSCRM.SolutionUniqueName` header drops the connector straight into
the named solution in a single request.

Usage
-----
  python scripts/register_custom_connector.py <connector-folder> [solution-name]

  solution-name defaults to "LaunchControl".

Idempotency
-----------
  1. If <folder>/.connector-id exists, PATCH that connectorid.
  2. Else look up by Dataverse `name` (publisher-prefixed slug). PATCH if found.
  3. Else POST a fresh row and cache its id in <folder>/.connector-id.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.auth import get_token, load_env

DEFAULT_SOLUTION = "LaunchControl"
SOLUTION_COMPONENT_CONNECTOR = 372  # ComponentType for Connector


# ---------- HTTP plumbing ----------

def _client():
    load_env()
    env = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = get_token()
    headers_base = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }

    def req(method, path, body=None, extra_headers=None):
        url = f"{env}/api/data/v9.2/{path.lstrip('/')}".replace(" ", "%20")
        h = dict(headers_base)
        if extra_headers:
            h.update(extra_headers)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        r = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(r) as resp:
                txt = resp.read().decode("utf-8")
                return resp.status, (json.loads(txt) if txt else {}), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), dict(e.headers)

    return env, req


def _entity_id_from_headers(headers):
    loc = headers.get("OData-EntityId") or headers.get("odata-entityid", "")
    return loc.rsplit("(", 1)[1].rstrip(")") if "(" in loc else None


# ---------- Naming ----------

def _connector_name(prefix, title):
    """Connector schema name: `<prefix>_<slug>`, alphanumeric, <=30 chars total.
    Dataverse enforces a 30-char cap on connector.name, so we can't faithfully
    URL-escape the title the way the maker portal does for short ones — we
    derive a stable slug instead. Display name keeps the human title.
    """
    slug = re.sub(r"[^a-z0-9]", "", title.lower())
    # Connector.name max length is 30 *exclusive* — Dataverse rejects exactly 30.
    max_total = 29
    max_slug = max_total - len(prefix) - 1
    if max_slug < 1:
        raise ValueError(f"publisher prefix '{prefix}' leaves no room for a name")
    return f"{prefix}_{slug[:max_slug]}"


# ---------- Main ----------

def register(folder, solution_name=DEFAULT_SOLUTION):
    folder = Path(folder).resolve()
    swagger_path = folder / "apiDefinition.swagger.json"
    props_path = folder / "apiProperties.json"
    if not swagger_path.exists():
        sys.exit(f"missing {swagger_path}")
    if not props_path.exists():
        sys.exit(f"missing {props_path}")

    swagger = json.loads(swagger_path.read_text(encoding="utf-8"))
    api_props_outer = json.loads(props_path.read_text(encoding="utf-8"))
    api_props = api_props_outer.get("properties", api_props_outer)

    title = swagger["info"]["title"]
    if len(title) > 30:
        sys.exit(
            f"swagger info.title is {len(title)} chars ('{title}') — the Dataverse "
            f"`connector.displayname` column caps at 30. Shorten it in apiDefinition.swagger.json."
        )
    description = (swagger.get("info") or {}).get("description", "") or ""
    icon_brand = api_props.get("iconBrandColor", "#0078D4")
    connection_parameters = api_props.get("connectionParameters", {}) or {}
    script_operations = api_props.get("scriptOperations", []) or []
    policy_templates = api_props.get("policyTemplateInstances", []) or []

    env, req = _client()
    print(f"[env] {env}")
    print(f"[connector] '{title}'")
    print(f"[solution] {solution_name}")

    # 1. Resolve solution + publisher prefix.
    sol_q = f"solutions?$filter=uniquename eq '{solution_name}'&$select=solutionid,_publisherid_value"
    s, b, _ = req("GET", sol_q)
    if s != 200 or not (b.get("value") if isinstance(b, dict) else None):
        sys.exit(f"solution lookup failed: {s} {b}")
    sol = b["value"][0]
    solution_id = sol["solutionid"]
    publisher_id = sol["_publisherid_value"]

    s, b, _ = req("GET", f"publishers({publisher_id})?$select=customizationprefix,uniquename")
    if s != 200:
        sys.exit(f"publisher lookup failed: {s} {b}")
    prefix = b["customizationprefix"] or "new"
    print(f"[publisher] {b['uniquename']} (prefix={prefix})")

    name = _connector_name(prefix, title)
    print(f"[name] {name}")

    # 2. Resolve existing connector id: cache file -> name lookup -> none.
    cache_file = folder / ".connector-id"
    connector_id = None
    if cache_file.exists():
        cached = cache_file.read_text().strip()
        # Validate the cached id is a real GUID currently in this env.
        s, b, _ = req("GET", f"connectors({cached})?$select=connectorid")
        if s == 200:
            connector_id = cached
            print(f"[cache] hit: {connector_id}")
        else:
            print(f"[cache] stale ({s}) — will rediscover")

    if not connector_id:
        s, b, _ = req("GET", f"connectors?$filter=name eq '{name}'&$select=connectorid")
        if s == 200 and (b.get("value") if isinstance(b, dict) else None):
            connector_id = b["value"][0]["connectorid"]
            print(f"[lookup] found existing: {connector_id}")

    # 3. Build the connector row body. The openapi/connection/script/policy
    # fields are stored as JSON-string payloads on the entity.
    body = {
        "name": name,
        "displayname": title,
        "description": description,
        "iconbrandcolor": icon_brand,
        "connectortype": 1,   # 1 = Custom
        "openapidefinition": json.dumps(swagger),
        "connectionparameters": json.dumps(connection_parameters),
        "scriptoperations": json.dumps(script_operations),
        "policytemplateinstances": json.dumps(policy_templates),
    }
    solution_header = {"MSCRM.SolutionUniqueName": solution_name}

    if connector_id:
        # PATCH stays in solution as long as the row was originally created there.
        s, b, _ = req("PATCH", f"connectors({connector_id})", body, solution_header)
        print(f"[PATCH] {s}")
        if s >= 400:
            sys.exit(f"update failed: {b}")
    else:
        s, b, hdrs = req("POST", "connectors", body, solution_header)
        print(f"[POST] {s}")
        if s >= 400:
            sys.exit(f"create failed: {b}")
        connector_id = _entity_id_from_headers(hdrs)

    cache_file.write_text(connector_id)

    # 4. Belt + braces: AddSolutionComponent in case the row was created
    # outside LaunchControl earlier and we just PATCHed it.
    s, b, _ = req("POST", "AddSolutionComponent", {
        "ComponentId": connector_id,
        "ComponentType": SOLUTION_COMPONENT_CONNECTOR,
        "SolutionUniqueName": solution_name,
        "AddRequiredComponents": False,
    })
    if s == 200:
        print(f"[solution] added to {solution_name}")
    elif s >= 400 and "already" in str(b).lower():
        print(f"[solution] already in {solution_name}")
    else:
        print(f"[solution] AddSolutionComponent: {s} {str(b)[:200]}")

    print()
    print("[done]")
    print(f"  connectorid = {connector_id}")
    print(f"  name        = {name}")
    print(f"  solution    = {solution_name} ({solution_id})")
    return connector_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: register_custom_connector.py <connector-folder> [solution-name]")
        sys.exit(2)
    register(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SOLUTION)
