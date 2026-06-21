"""Deploy the 'Dataverse Accounts' Cowork plugin substrate, end-to-end as far
as it is scriptable, for a single target environment.

This is the simple counterpart to episodes/ep-06-cowork-plugin/deploy.py:
same Part 1 mechanics (Entra app, Dataverse app user, MCP allowlist, Teams
Dev Portal OAuth registration) but self-contained and parameterized to the
target env below. It does NOT read the repo root .env (which targets a
different Launch Control environment).

Phases:
  A. Entra app registration (az ad app ...): adds Dynamics CRM
     user_impersonation (delegated), the Teams platform web redirect URI,
     a 1-year client secret, and attempts admin consent.
  B. Dataverse Application User bound to the new app, with System
     Administrator (demo-grade; tighten before broad rollout).
  D. allowedmcpclients: enable the built-in 'microsoftcowork' row and add
     the new Entra appId as an enabled allowed MCP client.
  E. Teams Dev Portal OAuth registration via atk oauth/register, producing
     the base64 referenceId for OAuthPluginVault.

Secrets go ONLY to .deploy/cowork-accounts/<timestamp>.json (gitignored) and
env/.env.dev.user (gitignored). They are never printed.

Auth: expects `az login` and `atk auth login m365` already done as a user
who can read/write the target Dataverse env and register Entra apps.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---- Target environment (authoritative for this sample) --------------------
TENANT_ID = "01eed126-9f96-4d2d-a127-dc2e786a898b"
DATAVERSE_URL = "https://org77c9659c.crm.dynamics.com"
ENVIRONMENT_ID = "5af9d25e-9d3c-ea33-83a7-e8001dfa6508"
ORGANIZATION_ID = "e616ec95-4b6b-f111-9bb1-000d3a31ff0e"

APP_DISPLAY_NAME = "Cowork-Accounts-MCP"
SYSTEM_ADMINISTRATOR_ROLE = "System Administrator"
MCP_CLIENT_UNIQUENAME = "coworkaccountsmcp"

# Well-known Dynamics CRM resource app id + user_impersonation scope id.
DYNAMICS_CRM_APP_ID = "00000007-0000-0000-c000-000000000000"
DYNAMICS_CRM_USER_IMPERSONATION_ID = "78ce3f0f-a1ce-49c2-8cde-64b5c0896db4"
# Teams platform OAuth callback. Without this Web redirect URI the Cowork
# "Connect" step fails with AADSTS50011.
TEAMS_PLATFORM_REDIRECT_URI = "https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect"

MCP_URL_SUFFIX = "/api/mcp"

THIS_DIR = Path(__file__).resolve().parent
PKG_DIR = THIS_DIR.parent
MANIFEST_PATH = PKG_DIR / "manifest.json"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY_DIR = REPO_ROOT / ".deploy" / "cowork-accounts"
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

ATK_PROJECT_DIR = THIS_DIR
ATK_ENV_DIR = ATK_PROJECT_DIR / "env"
ATK_ENV_NAME = "dev"
OAUTH_CONFIG_VAR = "ACCOUNTS_OAUTH_CONFIG_ID"

_DV_TOKEN: str | None = None


def banner(msg: str) -> None:
    print()
    print("=" * 72)
    print(f"  {msg}")
    print("=" * 72)


def step(label: str) -> None:
    print(f"\n--- {label} ---")


def az(*args: str) -> str:
    full = ["az", *args]
    print("  $", " ".join(full))
    proc = subprocess.run(full, shell=True, text=True, capture_output=True)
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, full, proc.stdout, proc.stderr)
    return proc.stdout.strip()


def dv_token(force: bool = False) -> str:
    global _DV_TOKEN
    if _DV_TOKEN and not force:
        return _DV_TOKEN
    proc = subprocess.run(
        ["az", "account", "get-access-token", "--resource", DATAVERSE_URL,
         "--query", "accessToken", "-o", "tsv"],
        shell=True, text=True, capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"Failed to acquire Dataverse token: {proc.stderr.strip()}")
    _DV_TOKEN = proc.stdout.strip()
    return _DV_TOKEN


def dv_request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    tok = dv_token()
    req = urllib.request.Request(
        f"{DATAVERSE_URL}/api/data/v9.2/{path.lstrip('/')}",
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

    step("Add Dynamics CRM delegated permission (user_impersonation)")
    az(
        "ad", "app", "permission", "add",
        "--id", app_id,
        "--api", DYNAMICS_CRM_APP_ID,
        "--api-permissions", f"{DYNAMICS_CRM_USER_IMPERSONATION_ID}=Scope",
    )

    step("Set Web redirect URI for Teams Dev Portal OAuth (Teams platform)")
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
    except subprocess.CalledProcessError:
        consent_ok = False
        print("  WARN  admin consent failed (need Privileged Role Admin / Global Admin)")
        print("        Run later from a privileged account:")
        print(f"          az ad app permission admin-consent --id {app_id}")
        print("        Or rely on per-user consent at the Cowork Connect step.")

    step("Create client secret (1 year)")
    secret_blob = json.loads(az(
        "ad", "app", "credential", "reset",
        "--id", app_id,
        "--display-name", f"cowork-accounts-{datetime.now(timezone.utc):%Y%m%d}",
        "--years", "1",
        "--append",
        "-o", "json",
    ))
    print(f"  secret created (expires {secret_blob.get('endDateTime')})")

    return {
        "appId": app_id,
        "objectId": object_id,
        "servicePrincipalId": sp_id,
        "tenantId": secret_blob.get("tenant") or TENANT_ID,
        "clientSecret": secret_blob.get("password"),
        "secretExpires": secret_blob.get("endDateTime"),
        "adminConsentGranted": consent_ok,
    }


def phase_b_dataverse_app_user(app_id: str) -> dict:
    banner("Phase B: Dataverse Application User")

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
            "businessunits?$select=businessunitid,name&$filter="
            + urllib.parse.quote("_parentbusinessunitid_value eq null"),
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
        {"@odata.id": f"{DATAVERSE_URL}/api/data/v9.2/roles({role_id})"},
    )
    if status in (204, 200, 412):
        print(f"  OK  role assigned (status={status})")
        ok = True
    else:
        print(f"  WARN  HTTP {status}: {payload}")
        ok = False

    return {"systemUserId": user_id, "roleId": role_id, "roleAssigned": ok}


def _add_allowlist_row(app_id: str) -> str | None:
    """Create the allowedmcpclients row, retrying uniquename with the env
    default publisher prefix if a bare uniquename is rejected."""
    for uniquename in (MCP_CLIENT_UNIQUENAME, f"new_{MCP_CLIENT_UNIQUENAME}"):
        s, payload = dv_request("POST", "allowedmcpclients", {
            "name": APP_DISPLAY_NAME,
            "uniquename": uniquename,
            "applicationid": app_id,
            "isenabled": True,
        })
        if s in (200, 201, 204):
            cid = payload.get("allowedmcpclientid") if isinstance(payload, dict) else None
            print(f"  OK  created (uniquename={uniquename}, id={cid})")
            return cid
        print(f"  retry  uniquename='{uniquename}' rejected: HTTP {s}: {payload}")
    return None


def phase_d_mcp_allowlist(app_id: str) -> dict:
    banner("Phase D: Dataverse MCP allowlist")
    result: dict = {}

    step("Enable built-in 'microsoftcowork' row")
    s, payload = dv_request(
        "GET",
        "allowedmcpclients?$select=allowedmcpclientid,name,isenabled&$filter="
        + urllib.parse.quote("uniquename eq 'microsoftcowork'"),
    )
    if s == 200 and payload.get("value"):
        row = payload["value"][0]
        if not row["isenabled"]:
            dv_request("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
            print(f"  OK  enabled (id={row['allowedmcpclientid']})")
        else:
            print(f"  OK  already enabled (id={row['allowedmcpclientid']})")
        result["microsoftCoworkId"] = row["allowedmcpclientid"]
    else:
        print("  WARN  'microsoftcowork' row not found (env-level MCP may be off; see RUNBOOK)")

    step(f"Add '{APP_DISPLAY_NAME}' (appId={app_id}) as allowed MCP client")
    s, payload = dv_request(
        "GET",
        "allowedmcpclients?$select=allowedmcpclientid,name,isenabled&$filter="
        + urllib.parse.quote(f"applicationid eq '{app_id}'"),
    )
    if s == 200 and payload.get("value"):
        row = payload["value"][0]
        if not row["isenabled"]:
            dv_request("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
        print(f"  OK  existing row (id={row['allowedmcpclientid']})")
        result["myClientId"] = row["allowedmcpclientid"]
    else:
        cid = _add_allowlist_row(app_id)
        if cid is None:
            print("  FAIL  could not add allowed MCP client row")
            sys.exit(1)
        result["myClientId"] = cid

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
    body = [f"# {header}", "# Managed by plugins/cowork-dataverse-accounts/deploy/deploy.py.", ""]
    for k, v in values.items():
        body.append(f"{k}={v}")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _load_teams_app_id() -> str:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"manifest not found at {MANIFEST_PATH}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["id"]


def _redact(text: str, secret: str | None) -> str:
    if not secret or not text:
        return text
    return text.replace(secret, "***REDACTED***")


def _build_oauth_update_yml() -> str:
    """oauth/update block targeting the existing config id, with a bumped
    name so atk's diff routine fires the PATCH and resyncs clientId+secret."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return (
        "version: v1.11\n\n"
        "environmentFolderPath: ./env\n\n"
        "provision:\n"
        "  - uses: oauth/update\n"
        "    with:\n"
        f"      name: Cowork-Accounts-OAuth-sync-{stamp}\n"
        f"      configurationId: ${{{{{OAUTH_CONFIG_VAR}}}}}\n"
        "      appId: ${{TEAMS_APP_ID}}\n"
        "      clientId: ${{AAD_APP_CLIENT_ID}}\n"
        "      clientSecret: ${{SECRET_AAD_APP_CLIENT_SECRET}}\n"
        "      baseUrl: ${{DATAVERSE_BASE_URL}}\n"
        "      authorizationUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/authorize\n"
        "      tokenUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token\n"
        "      refreshUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token\n"
        "      scope: ${{DATAVERSE_OAUTH_SCOPE}}\n"
        "      applicableToApps: SpecificApp\n"
        "      targetAudience: HomeTenant\n"
    )


def phase_e_atk_oauth(entra: dict) -> dict:
    banner("Phase E: Teams Dev Portal OAuth registration (atk oauth/register)")
    tenant_id = entra.get("tenantId") or TENANT_ID
    app_id = entra["appId"]
    secret = entra.get("clientSecret")

    teams_app_id = _load_teams_app_id()
    print(f"  TEAMS_APP_ID      = {teams_app_id} (from {MANIFEST_PATH.name})")
    print(f"  AAD_APP_CLIENT_ID = {app_id}")
    print(f"  DATAVERSE_BASE_URL= {DATAVERSE_URL}")

    env_dev_path = ATK_ENV_DIR / f".env.{ATK_ENV_NAME}"
    env_user_path = ATK_ENV_DIR / f".env.{ATK_ENV_NAME}.user"
    gitignore_path = ATK_ENV_DIR / ".gitignore"

    existing_dev = _read_env_file(env_dev_path)
    prior_config = existing_dev.get(OAUTH_CONFIG_VAR)

    dev_values = {
        "TEAMS_APP_ID": teams_app_id,
        "AAD_APP_CLIENT_ID": app_id,
        "TENANT_ID": tenant_id,
        "DATAVERSE_BASE_URL": DATAVERSE_URL,
        "DATAVERSE_MCP_URL": f"{DATAVERSE_URL}{MCP_URL_SUFFIX}",
        "DATAVERSE_OAUTH_SCOPE": f"openid offline_access {DATAVERSE_URL}/.default",
        "TEAMSFX_ENV": ATK_ENV_NAME,
    }
    if prior_config:
        dev_values[OAUTH_CONFIG_VAR] = prior_config
        print("  reusing existing OAuth config id (clear it to force re-register)")

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
    print(f"  wrote {env_dev_path}")
    print(f"  wrote {env_user_path} (secret redacted)")

    yml_path = ATK_PROJECT_DIR / "m365agents.yml"
    original_yml = yml_path.read_text(encoding="utf-8")
    rewrote_yml = False
    if prior_config:
        update_yml = _build_oauth_update_yml()
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
        return {"status": "failed", "atk_rc": proc.returncode,
                "atk_stdout": stdout, "atk_stderr": stderr}

    for line in stdout.strip().splitlines()[-8:]:
        print(f"  | {line}")

    after_dev = _read_env_file(env_dev_path)
    full_config_id = after_dev.get(OAUTH_CONFIG_VAR, "").strip()
    if not full_config_id:
        print(f"  FAIL  {OAUTH_CONFIG_VAR} missing from env/.env.dev after provision")
        return {"status": "failed", "reason": "no config id", "atk_stdout": stdout}

    reference_id = full_config_id  # base64 form -> OAuthPluginVault.referenceId verbatim
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

    return {
        "status": "ok",
        "action": action,
        "referenceId": reference_id,
        "decoded": decoded,
        "oAuthConfigId": oauth_config_id,
        "tenantId": cfg_tenant,
        "teamsAppId": teams_app_id,
    }


def main() -> int:
    banner("Deploy 'Dataverse Accounts' Cowork plugin (scriptable Part 1)")
    print(f"  Tenant:        {TENANT_ID}")
    print(f"  Dataverse env: {DATAVERSE_URL}")
    print(f"  Environment:   {ENVIRONMENT_ID}")
    print(f"  Output dir:    {DEPLOY_DIR}")

    # Fail fast if Dataverse is unreachable as the signed-in user.
    s, who = dv_request("GET", "WhoAmI")
    if s != 200 or not isinstance(who, dict) or who.get("OrganizationId", "").lower() != ORGANIZATION_ID:
        print(f"  FAIL  WhoAmI did not confirm target org. HTTP {s}: {who}")
        print("        Run `az login` as a user with access to this environment first.")
        return 1
    print(f"  WhoAmI OK      user={who.get('UserId')} org={who.get('OrganizationId')}")

    artifacts = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenantId": TENANT_ID,
        "dataverseUrl": DATAVERSE_URL,
        "environmentId": ENVIRONMENT_ID,
    }
    artifacts["entra"] = phase_a_entra_app()
    artifacts["dataverse"] = phase_b_dataverse_app_user(artifacts["entra"]["appId"])
    artifacts["mcpAllowlist"] = phase_d_mcp_allowlist(artifacts["entra"]["appId"])
    artifacts["oauth"] = phase_e_atk_oauth(artifacts["entra"])

    out_path = DEPLOY_DIR / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out_path.write_text(json.dumps(artifacts, indent=2))
    print(f"\n  Wrote artifacts to {out_path}")

    if artifacts["oauth"].get("status") != "ok":
        banner("Phase E (atk oauth/register) FAILED - see logs above")
        return 1

    ref = artifacts["oauth"]["referenceId"]
    banner("Scriptable Part 1 complete")
    print(f"""
  [x] Entra app                     appId={artifacts['entra']['appId']}
  [x] Dataverse app user + role     systemuserid={artifacts['dataverse'].get('systemUserId')}
  [x] allowedmcpclients toggle
  [x] Teams Dev Portal OAuth        oAuthConfigId={artifacts['oauth']['oAuthConfigId']}

  Next (repo):
    cd {PKG_DIR}
    .\\build.ps1 -OAuthReferenceId "{ref}"
    python deploy\\preflight.py --run

  Then follow deploy/RUNBOOK.md for the portal-only steps (upload, connect,
  test "list my accounts", harden the OAuth registration to TeamsAppId
  {artifacts['oauth']['teamsAppId']}).
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
