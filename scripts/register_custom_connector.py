"""Register a custom connector in the target environment, programmatically.

Works for BOTH:
  - Plain REST connectors (e.g. connectors/github-releases-rest)
  - Remote MCP servers (e.g. connectors/learn-mcp, connectors/github-mcp --
    the x-ms-agentic-protocol extension in the swagger is what makes them MCP)

Why this exists:
  Ep 5 part 3 originally documented `paconn create` as a manual CLI hop with a
  separately-edited settings.json per connector. This script is the one-liner
  alternative: point it at any connectors/<folder> and it (a) generates a
  settings.json with the right env id baked in, (b) shells out to paconn,
  (c) verifies via PAPI that the connector landed, (d) writes the resulting
  connector id to <folder>/.connector-id for downstream scripts.

  Power Apps' connector-create flow uploads the swagger to a temporary blob
  store before registering -- paconn handles all that. Skipping paconn means
  reimplementing that blob handshake, which isn't worth it for an episode demo.

Usage:
  python scripts/register_custom_connector.py <folder>
  python scripts/register_custom_connector.py connectors/github-releases-rest

Idempotency:
  paconn create with an existing target connector updates in place. If a
  <folder>/.connector-id file exists it is reused; otherwise this script
  searches PAPI for a custom connector with the same display name first.

Prereqs:
  - `az login` (current tenant)
  - `paconn login` (interactive once per session; this script will prompt if
    paconn says the auth cache is empty)

Env:
  ENVIRONMENT_ID -- defaults to LaunchControl 2.0
"""
import json, os, sys, subprocess, urllib.request, urllib.error, urllib.parse, time
from pathlib import Path
from azure.identity import AzureCliCredential

ENV_ID = os.environ.get("ENVIRONMENT_ID", "2e2dd60a-e6c7-eeb7-b61d-d4709d8dae07")
API_VER = "2016-11-01"
PAPI = "https://api.powerapps.com"


def _req(token, method, url, body=None):
    h = {"Authorization": "Bearer " + token, "Accept": "application/json",
         "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method))
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def _find_existing(papi_token: str, display_name: str):
    q = urllib.parse.quote(f"environment eq '{ENV_ID}'")
    s, b = _req(papi_token, "GET",
                f"{PAPI}/providers/Microsoft.PowerApps/apis?api-version={API_VER}&%24filter={q}&%24top=2000")
    if s != 200:
        return None
    for a in json.loads(b).get("value", []):
        p = a.get("properties", {})
        if p.get("isCustomApi") and p.get("displayName") == display_name:
            return a["name"]
    return None


def register(folder: Path):
    folder = folder.resolve()
    swagger = json.loads((folder / "apiDefinition.swagger.json").read_text())
    display = swagger["info"]["title"]

    cred = AzureCliCredential()
    papi_token = cred.get_token("https://service.powerapps.com/.default").token

    # 1. Find existing connector id (if any)
    cached = folder / ".connector-id"
    existing_id = cached.read_text().strip() if cached.exists() else _find_existing(papi_token, display)
    if existing_id:
        print(f"[update] Found existing connector: {existing_id}")
    else:
        print(f"[create] No existing connector with displayName='{display}' -- will create.")

    # 2. Generate settings.json for paconn (env id baked in)
    settings = {
        "environment": ENV_ID,
        "apiProperties": "apiProperties.json",
        "apiDefinition": "apiDefinition.swagger.json",
        "powerAppsApiVersion": API_VER,
        "powerAppsUrl": PAPI,
    }
    if existing_id:
        settings["connectorId"] = existing_id
    settings_path = folder / "_settings.generated.json"
    settings_path.write_text(json.dumps(settings, indent=2))

    # 3. Shell out to paconn. paconn is known to hang on a final HTTP read
    # for ~2 minutes after success; we cap with a 90s timeout and verify out-of-band.
    cmd = ["paconn", "create", "-s", str(settings_path)]
    print(f"[paconn] {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, cwd=str(folder), capture_output=True, text=True, timeout=90)
        print(proc.stdout)
        if proc.stderr:
            print("STDERR:", proc.stderr)
    except subprocess.TimeoutExpired as e:
        print("[paconn] hit known 2-min hang -- killed after 90s; verifying via PAPI...")
        if e.stdout: print(e.stdout)

    # 4. Verify
    time.sleep(2)
    final_id = _find_existing(papi_token, display)
    if not final_id:
        print("[FAIL] Connector did not appear in PAPI after paconn run.")
        sys.exit(1)
    cached.write_text(final_id)
    print(f"[ok] Connector registered: {final_id}")
    print(f"     Maker UI: https://make.powerapps.com/environments/{ENV_ID}/customconnectors")
    return final_id


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: register_custom_connector.py <connector-folder>")
        sys.exit(2)
    register(Path(sys.argv[1]))
