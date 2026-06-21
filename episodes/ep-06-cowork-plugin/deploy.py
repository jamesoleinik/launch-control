"""Deploy the Episode 6 plugin substrate end-to-end as far as it is scriptable.

Phases:
  A. Entra app registration (az ad app create)
     - adds Dynamics CRM 'user_impersonation' delegated permission
     - creates client secret
     - attempts admin consent (skipped if caller lacks the role)
  B. Dataverse Application User
     - creates a systemuser row bound to the new app's Application ID
     - assigns the 'System Administrator' role (least surprise for a demo;
       tighten before broader rollout)
  C. Builds the Cowork plugin package zip via plugins/cowork-dataverse-mcp/build.ps1

Outputs everything to .deploy/ep-06/<timestamp>.json (gitignored) so you have
the IDs in one place for the portal-side steps you must do yourself:

  1. Power Platform admin center -> environment -> Settings -> Product ->
     Features -> Dataverse MCP -> add the Entra Application ID as an
     "Allowed MCP Client".  (No public API; UI only.)
  2. Teams Developer Portal -> OAuth registrations -> create a new
     registration with Base URL = DATAVERSE_URL, scope =
     "{DATAVERSE_URL}/.default offline_access", client id + secret from the
     Entra app this script just created.  (No public API.)
  3. Re-run build.ps1 with the Teams OAuth Registration ID from step 2.
  4. M365 Admin Center -> Integrated apps -> Upload custom apps ->
     the zip from build.ps1.  (Requires Teams or Global Admin; doable via
     m365 CLI / Graph if you have AppCatalog.Submit, but that requires
     extra consent.)
  5. In Cowork: Add plugin -> Launch Control -> Connect.  (User-interactive
     OAuth consent flow; not scriptable.)
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402

APP_DISPLAY_NAME = "LaunchControl-Cowork-MCP-v3"
# Dynamics CRM resource app id and user_impersonation scope id (well-known).
DYNAMICS_CRM_APP_ID = "00000007-0000-0000-c000-000000000000"
DYNAMICS_CRM_USER_IMPERSONATION_ID = "78ce3f0f-a1ce-49c2-8cde-64b5c0896db4"
SYSTEM_ADMINISTRATOR_ROLE = "System Administrator"
# Teams platform redirect URI is the OAuth callback used by Teams Dev
# Portal OAuth connections (including the one Cowork plugins consume via
# OAuthPluginVault). Without this Web redirect URI on the Entra app,
# sign-in at the Cowork "Connect" step fails with AADSTS50011.
TEAMS_PLATFORM_REDIRECT_URI = "https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect"

# Phase E (Teams Dev Portal OAuth registration via atk) lives next to this file.
EP06_DIR = Path(__file__).resolve().parent
ATK_PROJECT_DIR = EP06_DIR
ATK_ENV_DIR = ATK_PROJECT_DIR / "env"
ATK_ENV_NAME = "dev"
# Pin TEAMS_APP_ID to the manifest we actually publish. The active package
# is now `plugins/dataverse-launchcontrol/` (devPreview, agentConnectors[]
# + agentSkills[], v1.4.0+, manifest id 6b8a5896-...). The Teams Dev
# Portal OAuth registration's `applicableToApps` is pinned to this id; if
# you switch which package you upload to Cowork, update this constant in
# lockstep or Phase E will re-point the registration and break sign-in.
LIVE_MANIFEST = REPO_ROOT / "plugins" / "dataverse-launchcontrol" / "manifest.json"
MCP_URL_SUFFIX = "/api/mcp_preview"

DEPLOY_DIR = REPO_ROOT / ".deploy" / "ep-06"
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)


def banner(msg: str) -> None:
    print()
    print("=" * 72)
    print(f"  {msg}")
    print("=" * 72)


def step(label: str) -> None:
    print(f"\n--- {label} ---")


def az(*args: str, capture: bool = True) -> str:
    full = ["az", *args]
    print("  $", " ".join(full))
    if capture:
        # Do NOT merge stderr - az writes WARNING lines there that break JSON parsing.
        proc = subprocess.run(full, shell=True, text=True, capture_output=True)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, full, proc.stdout, proc.stderr)
        return proc.stdout.strip()
    subprocess.check_call(full, shell=True)
    return ""


def dv_request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    load_env()
    dv_url = os.environ["DATAVERSE_URL"].rstrip("/")
    tok = get_credential().get_token(f"{dv_url}/.default").token
    req = urllib.request.Request(
        f"{dv_url}/api/data/v9.2/{path.lstrip('/')}",
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        data=(json.dumps(body).encode() if body is not None else None),
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def phase_a_entra_app() -> dict:
    banner("Phase A: Entra app registration")

    step(f"Find or create app '{APP_DISPLAY_NAME}'")
    existing = json.loads(az("ad", "app", "list", "--display-name", APP_DISPLAY_NAME, "-o", "json"))
    if existing:
        app = existing[0]
        print(f"  reusing existing appId={app['appId']}")
    else:
        app = json.loads(az(
            "ad", "app", "create",
            "--display-name", APP_DISPLAY_NAME,
            "--sign-in-audience", "AzureADMyOrg",
            "-o", "json",
        ))
        print(f"  created appId={app['appId']}")

    app_id = app["appId"]
    object_id = app["id"]

    step("Add Dynamics CRM delegated permission")
    az(
        "ad", "app", "permission", "add",
        "--id", app_id,
        "--api", DYNAMICS_CRM_APP_ID,
        "--api-permissions", f"{DYNAMICS_CRM_USER_IMPERSONATION_ID}=Scope",
    )

    step("Set Web redirect URI for Teams Dev Portal OAuth (Teams platform)")
    # Without this, sign-in fails with AADSTS50011 at the Cowork plugin
    # "Connect" step. The Teams platform OAuth redirect is the callback URI
    # behind every Teams Dev Portal OAuth connection consumed by Cowork.
    az(
        "ad", "app", "update",
        "--id", app_id,
        "--web-redirect-uris", TEAMS_PLATFORM_REDIRECT_URI,
    )

    step("Ensure service principal exists")
    sps = json.loads(az("ad", "sp", "list", "--filter", f"appId eq '{app_id}'", "-o", "json"))
    if sps:
        sp_id = sps[0]["id"]
        print(f"  existing servicePrincipalId={sp_id}")
    else:
        sp = json.loads(az("ad", "sp", "create", "--id", app_id, "-o", "json"))
        sp_id = sp["id"]
        print(f"  created servicePrincipalId={sp_id}")

    step("Attempt admin consent (delegated)")
    try:
        az("ad", "app", "permission", "admin-consent", "--id", app_id)
        consent_ok = True
        print("  OK  admin consent granted")
    except subprocess.CalledProcessError as e:
        consent_ok = False
        print("  WARN  admin consent failed (need Privileged Role Admin / Global Admin)")
        print("        Run later from a privileged account:")
        print(f"          az ad app permission admin-consent --id {app_id}")
        print(f"        (CalledProcessError details suppressed)")

    step("Create client secret")
    secret_blob = json.loads(az(
        "ad", "app", "credential", "reset",
        "--id", app_id,
        "--display-name", f"cowork-mcp-{datetime.now(timezone.utc):%Y%m%d}",
        "--years", "1",
        "--append",
        "-o", "json",
    ))
    print(f"  secret created (expires {secret_blob.get('endDateTime')})")

    return {
        "appId": app_id,
        "objectId": object_id,
        "servicePrincipalId": sp_id,
        "tenantId": secret_blob.get("tenant"),
        "clientSecret": secret_blob.get("password"),
        "secretExpires": secret_blob.get("endDateTime"),
        "adminConsentGranted": consent_ok,
    }


def phase_b_dataverse_app_user(app_id: str) -> dict:
    banner("Phase B: Dataverse Application User")
    load_env()
    dv_url = os.environ["DATAVERSE_URL"].rstrip("/")

    step(f"Check for existing systemuser bound to applicationid={app_id}")
    q = urllib.parse.quote(f"applicationid eq {app_id}")
    status, payload = dv_request(
        "GET",
        f"systemusers?$select=systemuserid,fullname,applicationid&$filter={q}",
    )
    if status != 200:
        print(f"  FAIL  HTTP {status}: {payload}")
        sys.exit(1)
    rows = payload.get("value", [])
    if rows:
        user_id = rows[0]["systemuserid"]
        print(f"  reusing existing systemuserid={user_id}")
    else:
        step("Create Application User row")
        status, bu = dv_request(
            "GET",
            "businessunits?$select=businessunitid,name&$filter=" + urllib.parse.quote("_parentbusinessunitid_value eq null"),
        )
        if status != 200 or not bu.get("value"):
            print(f"  FAIL  could not find root business unit: HTTP {status}")
            sys.exit(1)
        root_bu = bu["value"][0]["businessunitid"]
        status, created = dv_request(
            "POST",
            "systemusers",
            {
                "applicationid": app_id,
                "businessunitid@odata.bind": f"/businessunits({root_bu})",
            },
        )
        if status not in (200, 201, 204):
            print(f"  FAIL  HTTP {status}: {created}")
            sys.exit(1)
        user_id = created.get("systemuserid")
        print(f"  created systemuserid={user_id}")

    step(f"Ensure '{SYSTEM_ADMINISTRATOR_ROLE}' role assigned")
    q = urllib.parse.quote(f"name eq '{SYSTEM_ADMINISTRATOR_ROLE}'")
    status, roles = dv_request("GET", f"roles?$select=roleid,name&$filter={q}")
    if status != 200 or not roles.get("value"):
        print(f"  WARN  could not find role '{SYSTEM_ADMINISTRATOR_ROLE}'")
        return {"systemUserId": user_id, "roleAssigned": False}
    role_id = roles["value"][0]["roleid"]
    status, payload = dv_request(
        "POST",
        f"systemusers({user_id})/systemuserroles_association/$ref",
        {"@odata.id": f"{dv_url}/api/data/v9.2/roles({role_id})"},
    )
    if status in (204, 200, 412):
        print(f"  OK  role assigned (status={status})")
        ok = True
    else:
        print(f"  WARN  HTTP {status}: {payload}")
        ok = False

    return {"systemUserId": user_id, "roleId": role_id, "roleAssigned": ok}


def phase_d_mcp_allowlist(app_id: str) -> dict:
    banner("Phase D: Dataverse MCP allowlist")
    result = {}

    step("Enable 'microsoftcowork' row")
    s, payload = dv_request(
        "GET",
        "allowedmcpclients?$select=allowedmcpclientid,name,isenabled&$filter=" +
        urllib.parse.quote("uniquename eq 'microsoftcowork'"),
    )
    if s == 200 and payload.get("value"):
        row = payload["value"][0]
        if not row["isenabled"]:
            s, _ = dv_request("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
            print(f"  OK  enabled (id={row['allowedmcpclientid']})")
        else:
            print(f"  OK  already enabled (id={row['allowedmcpclientid']})")
        result["microsoftCoworkId"] = row["allowedmcpclientid"]
    else:
        print(f"  WARN  microsoftcowork row not found")

    step(f"Add '{APP_DISPLAY_NAME}' as allowed MCP client")
    s, payload = dv_request(
        "GET",
        "allowedmcpclients?$select=allowedmcpclientid,name,isenabled&$filter=" +
        urllib.parse.quote(f"applicationid eq '{app_id}'"),
    )
    if s == 200 and payload.get("value"):
        row = payload["value"][0]
        if not row["isenabled"]:
            dv_request("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
        print(f"  OK  existing row (id={row['allowedmcpclientid']})")
        result["myClientId"] = row["allowedmcpclientid"]
    else:
        s, payload = dv_request("POST", "allowedmcpclients", {
            "name": APP_DISPLAY_NAME,
            "uniquename": "lc_launchcontrolcoworkmcp",
            "applicationid": app_id,
            "isenabled": True,
        })
        if s in (200, 201, 204):
            cid = payload.get("allowedmcpclientid") if isinstance(payload, dict) else None
            print(f"  OK  created (id={cid})")
            result["myClientId"] = cid
        else:
            print(f"  FAIL  HTTP {s}: {payload}")
            sys.exit(1)

    return result


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _write_env_file(path: Path, values: dict[str, str], header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {header}", "# Managed by episodes/ep-06-cowork-plugin/deploy.py Phase E.", ""]
    for k, v in values.items():
        body.append(f"{k}={v}")
    # UTF-8 without BOM, newline-terminated.
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _load_teams_app_id() -> str:
    if not LIVE_MANIFEST.exists():
        raise FileNotFoundError(f"Live manifest not found at {LIVE_MANIFEST}")
    return json.loads(LIVE_MANIFEST.read_text(encoding="utf-8"))["id"]


def _redact(text: str, secret: str | None) -> str:
    if not secret or not text:
        return text
    return text.replace(secret, "***REDACTED***")


def _build_oauth_update_yml(register_yml: str) -> str:
    """Rewrite the committed oauth/register provision block as an oauth/update
    block targeting the existing LC_OAUTH_CONFIG_ID. Returns "" if the
    expected register block can't be found (caller should keep the original).

    The `name` is bumped each call (timestamp suffix) so atk's diff routine
    detects a delta and fires the PATCH -- otherwise clientSecret-only changes
    are ignored and the row stays out of sync.
    """
    if "uses: oauth/register" not in register_yml:
        return ""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return (
        "version: v1.11\n\n"
        "environmentFolderPath: ./env\n\n"
        "provision:\n"
        "  - uses: oauth/update\n"
        "    with:\n"
        f"      name: LaunchControl-Cowork-OAuth-sync-{stamp}\n"
        "      configurationId: ${{LC_OAUTH_CONFIG_ID}}\n"
        "      appId: ${{TEAMS_APP_ID}}\n"
        "      clientId: ${{AAD_APP_CLIENT_ID}}\n"
        "      clientSecret: ${{SECRET_AAD_APP_CLIENT_SECRET}}\n"
        "      baseUrl: ${{DATAVERSE_MCP_URL}}\n"
        "      authorizationUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/authorize\n"
        "      tokenUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token\n"
        "      refreshUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token\n"
        "      scope: ${{DATAVERSE_OAUTH_SCOPE}}\n"
        "      applicableToApps: SpecificApp\n"
        "      targetAudience: HomeTenant\n"
        "projectId: ed6148e3-861d-4a75-859c-6819966a841e\n"
    )


def phase_e_atk_oauth(entra: dict) -> dict:
    banner("Phase E: Teams Dev Portal OAuth registration (atk oauth/register)")
    load_env()
    dv_url = os.environ["DATAVERSE_URL"].rstrip("/")
    tenant_id = entra["tenantId"] or os.environ.get("TENANT_ID", "")
    app_id = entra["appId"]
    secret = entra["clientSecret"]

    if not tenant_id:
        print("  FAIL  no tenantId available (neither Phase A nor .env)")
        return {"status": "failed", "reason": "missing tenantId"}

    teams_app_id = _load_teams_app_id()
    print(f"  TEAMS_APP_ID  = {teams_app_id} (from {LIVE_MANIFEST.name})")
    print(f"  AAD_APP_CLIENT_ID = {app_id}")
    print(f"  DATAVERSE_MCP_URL = {dv_url}{MCP_URL_SUFFIX}")

    # Step 1: merge env files. Preserve any existing LC_OAUTH_CONFIG_ID so
    # atk treats this as a no-op re-run rather than minting a duplicate row.
    env_dev_path = ATK_ENV_DIR / f".env.{ATK_ENV_NAME}"
    env_user_path = ATK_ENV_DIR / f".env.{ATK_ENV_NAME}.user"
    gitignore_path = ATK_ENV_DIR / ".gitignore"

    existing_dev = _read_env_file(env_dev_path)
    prior_config = existing_dev.get("LC_OAUTH_CONFIG_ID")

    dev_values = {
        "TEAMS_APP_ID": teams_app_id,
        "AAD_APP_CLIENT_ID": app_id,
        "TENANT_ID": tenant_id,
        "DATAVERSE_MCP_URL": f"{dv_url}{MCP_URL_SUFFIX}",
        "DATAVERSE_OAUTH_SCOPE": f"openid offline_access {dv_url}/.default",
    }
    if prior_config:
        dev_values["LC_OAUTH_CONFIG_ID"] = prior_config
        print(f"  reusing existing LC_OAUTH_CONFIG_ID (clear to force re-register)")

    _write_env_file(env_dev_path, dev_values, "atk env (dev) - non-secret")
    _write_env_file(
        env_user_path,
        {"SECRET_AAD_APP_CLIENT_SECRET": secret or ""},
        "atk env (dev) - secrets - DO NOT COMMIT",
    )
    if not gitignore_path.exists():
        gitignore_path.write_text(
            "# atk-managed env files. Secrets stay local.\n.env.*.user\n",
            encoding="utf-8",
        )
    print(f"  wrote {env_dev_path.relative_to(REPO_ROOT)}")
    print(f"  wrote {env_user_path.relative_to(REPO_ROOT)} (secret redacted)")

    # Step 2: invoke atk provision against m365agents.yml. If we already have
    # a prior LC_OAUTH_CONFIG_ID, atk's `oauth/register` would short-circuit
    # by name and leave the existing Dev Portal row pointing at whatever
    # clientId/secret it was first registered with -- including a deleted
    # Entra app after a teardown+redeploy. Swap to `oauth/update` (with a
    # bumped `name`) so atk's diff routine forces a PATCH and resyncs the
    # row's clientId+secret to the values we just wrote into env files.
    yml_path = ATK_PROJECT_DIR / "m365agents.yml"
    original_yml = yml_path.read_text(encoding="utf-8")
    rewrote_yml = False
    if prior_config:
        update_yml = _build_oauth_update_yml(original_yml)
        if update_yml and update_yml != original_yml:
            yml_path.write_text(update_yml, encoding="utf-8")
            rewrote_yml = True
            print("  swapped m365agents.yml -> oauth/update (resync clientId+secret)")

    step(f"atk provision --env {ATK_ENV_NAME} -i false")
    try:
        proc = subprocess.run(
            ["atk", "provision", "--env", ATK_ENV_NAME, "-i", "false"],
            cwd=str(ATK_PROJECT_DIR),
            capture_output=True,
            text=True,
            shell=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        if rewrote_yml:
            yml_path.write_text(original_yml, encoding="utf-8")
        print("  FAIL  atk provision timed out after 180s")
        return {"status": "failed", "reason": "timeout"}
    finally:
        if rewrote_yml:
            yml_path.write_text(original_yml, encoding="utf-8")

    stdout = _redact(proc.stdout or "", secret)
    stderr = _redact(proc.stderr or "", secret)
    if proc.returncode != 0:
        print(f"  FAIL  atk exited {proc.returncode}")
        if stdout.strip():
            print("  --- atk stdout ---")
            print(stdout)
        if stderr.strip():
            print("  --- atk stderr ---")
            print(stderr)
        return {
            "status": "failed",
            "atk_rc": proc.returncode,
            "atk_stdout": stdout,
            "atk_stderr": stderr,
        }
    # Show a short tail of atk output (already redacted) for visibility.
    tail = stdout.strip().splitlines()[-8:]
    for line in tail:
        print(f"  | {line}")

    # Step 3: re-read env/.env.dev and resolve LC_OAUTH_CONFIG_ID.
    after_dev = _read_env_file(env_dev_path)
    full_config_id = after_dev.get("LC_OAUTH_CONFIG_ID", "").strip()
    if not full_config_id:
        print("  FAIL  LC_OAUTH_CONFIG_ID missing from env/.env.dev after provision")
        return {"status": "failed", "reason": "no config id", "atk_stdout": stdout}

    # atk's writeToEnvironmentFile writes LC_OAUTH_CONFIG_ID already base64-encoded
    # (it's what goes into OAuthPluginVault.referenceId verbatim). Decode to get
    # the inner <tenant>###<oAuthConfigId> for diagnostics.
    import base64

    reference_id = full_config_id  # base64 form, drop straight into the manifest
    try:
        decoded = base64.b64decode(full_config_id).decode("utf-8", errors="replace")
    except Exception:
        decoded = ""
    if "###" in decoded:
        cfg_tenant, oauth_config_id = decoded.split("###", 1)
    elif "##" in decoded:
        cfg_tenant, oauth_config_id = decoded.split("##", 1)
    else:
        cfg_tenant, oauth_config_id = "", decoded

    action = "reused" if prior_config == full_config_id else "registered"

    step("OAuth registration result")
    print(f"  action            = {action}")
    print(f"  referenceId (b64) = {reference_id}")
    print(f"  decoded           = {decoded}")
    print(f"  tenant            = {cfg_tenant}")
    print(f"  oAuthConfigId     = {oauth_config_id}")
    print()
    print("  Drop this verbatim into OAuthPluginVault.referenceId:")
    print(f"    {reference_id}")

    return {
        "status": "ok",
        "action": action,
        "referenceId": reference_id,
        "decoded": decoded,
        "oAuthConfigId": oauth_config_id,
        "tenantId": cfg_tenant,
        "teamsAppId": teams_app_id,
        "atk_rc": 0,
    }



def phase_c_build_package(app_id: str, oauth_id: str | None = None) -> dict:
    banner("Phase C: Build Cowork plugin package")
    load_env()
    dv_url = os.environ["DATAVERSE_URL"].rstrip("/")
    if oauth_id:
        registration_id = oauth_id
        print(f"  Using Teams OAuth Registration ID from Phase E: {oauth_id}")
    else:
        registration_id = "00000000-PENDING-TEAMS-OAUTH-REG-0000000000"
        print(f"  NOTE  Phase E did not produce an OAuth id; using placeholder.")
        print(f"        Re-run build.ps1 with the real ID once you have one.")
    out = subprocess.check_output(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(REPO_ROOT / "plugins" / "cowork-dataverse-mcp" / "build.ps1"),
            "-DataverseUrl", dv_url,
            "-OAuthRegistrationId", registration_id,
        ],
        text=True, stderr=subprocess.STDOUT, shell=True,
    )
    print(out)
    zip_path = REPO_ROOT / "plugins" / "cowork-dataverse-mcp" / "out" / "launch-control-cowork-plugin.zip"
    return {"zip": str(zip_path), "oauthRegistrationId": registration_id}


def main() -> int:
    banner("Episode 6 -- deploy as much as is scriptable")
    load_env()
    dv_url = os.environ.get("DATAVERSE_URL", "").rstrip("/")
    print(f"  Dataverse env: {dv_url}")
    print(f"  Output dir:    {DEPLOY_DIR}")

    artifacts = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataverseUrl": dv_url,
    }
    artifacts["entra"] = phase_a_entra_app()
    artifacts["dataverse"] = phase_b_dataverse_app_user(artifacts["entra"]["appId"])
    artifacts["mcpAllowlist"] = phase_d_mcp_allowlist(artifacts["entra"]["appId"])
    artifacts["oauth"] = phase_e_atk_oauth(artifacts["entra"])
    # Build with the real OAuth registration if Phase E succeeded.
    oauth_id_for_build = (
        artifacts["oauth"].get("oAuthConfigId")
        if artifacts["oauth"].get("status") == "ok"
        else None
    )
    artifacts["package"] = phase_c_build_package(
        artifacts["entra"]["appId"], oauth_id_for_build
    )

    out_path = DEPLOY_DIR / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out_path.write_text(json.dumps(artifacts, indent=2))
    print()
    print(f"  Wrote artifacts to {out_path}")

    if artifacts["oauth"].get("status") != "ok":
        banner("Phase E (atk oauth/register) FAILED -- see logs above")
        return 1

    banner("Remaining portal-side steps")
    print(f"""
  Phase A-E completed end-to-end (no portal click-throughs):
    [x] Entra app (Graph)                               -> appId={artifacts['entra']['appId']}
    [x] Dataverse app user + System Administrator (Web API)
    [x] allowedmcpclients toggle (Web API)
    [x] Teams Dev Portal OAuth (atk oauth/register)     -> {artifacts['oauth']['oAuthConfigId']}

  Drop into the v2 manifest's OAuthPluginVault.referenceId (verbatim):
    {artifacts['oauth']['referenceId']}

  Then upload the package:
    1. M365 Admin Center -> Integrated apps -> Upload custom apps
       -> plugins/cowork-dataverse-mcp-v2/<your zip>
    2. Cowork -> Add plugin -> Launch Control -> Connect
    3. (Harden) Teams Dev Portal -> OAuth registration -> App restrictions
       -> change "Any Teams app" to {artifacts['oauth']['teamsAppId']}

  Demo prompt:
     "What is blocking Q3 Widget Launch, and should we slip?"
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
