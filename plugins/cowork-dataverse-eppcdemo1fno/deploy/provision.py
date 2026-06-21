"""Provision the scriptable Cowork plugin substrate for one Dataverse env.

Reads ./config.json in this folder for all env-specific values, then runs:
  A. Entra app registration (unique per env)
  B. Dataverse application user + System Administrator
  D. allowedmcpclients row for the app
  E. Teams Dev Portal OAuth registration via atk -> base64 referenceId

This is the parameterized sibling of the accounts deploy.py. It writes
m365agents.yml + env files in this folder itself, so it is self-contained.
Secrets go only to .deploy/<tag>/<ts>.json and env/.env.dev.user (gitignored)
and are never printed.

Auth: expects `az login` and `atk auth login m365` done as an identity that can
register Entra apps and is a System Administrator in the target env.
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

THIS_DIR = Path(__file__).resolve().parent
PKG_DIR = THIS_DIR.parent
MANIFEST_PATH = PKG_DIR / "manifest.json"
REPO_ROOT = Path(__file__).resolve().parents[3]
CFG = json.loads((THIS_DIR / "config.json").read_text(encoding="utf-8"))

TENANT_ID = CFG["tenant_id"]
DATAVERSE_URL = CFG["dataverse_url"].rstrip("/")
ENVIRONMENT_ID = CFG["environment_id"]
ORGANIZATION_ID = CFG["organization_id"].lower()
APP_DISPLAY_NAME = CFG["app_display_name"]
MCP_CLIENT_UNIQUENAME = CFG["mcp_client_uniquename"]
MCP_URL_SUFFIX = CFG.get("mcp_url_suffix", "/api/mcp_preview")
OAUTH_NAME = CFG["oauth_name"]
DEPLOY_TAG = CFG["deploy_tag"]
OAUTH_CONFIG_VAR = CFG.get("oauth_config_var", "OAUTH_CONFIG_ID")
PROJECT_ID = CFG["project_id"]

SYSTEM_ADMINISTRATOR_ROLE = "System Administrator"
DYNAMICS_CRM_APP_ID = "00000007-0000-0000-c000-000000000000"
DYNAMICS_CRM_USER_IMPERSONATION_ID = "78ce3f0f-a1ce-49c2-8cde-64b5c0896db4"
TEAMS_PLATFORM_REDIRECT_URI = "https://teams.microsoft.com/api/platform/v1.0/oAuthRedirect"

DEPLOY_DIR = REPO_ROOT / ".deploy" / DEPLOY_TAG
DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
ATK_ENV_DIR = THIS_DIR / "env"
ATK_ENV_NAME = "dev"

_DV_TOKEN: str | None = None


def banner(m): print("\n" + "=" * 72 + f"\n  {m}\n" + "=" * 72)
def step(m): print(f"\n--- {m} ---")


def az(*args):
    full = ["az", *args]
    print("  $", " ".join(full))
    p = subprocess.run(full, shell=True, text=True, capture_output=True)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, full, p.stdout, p.stderr)
    return p.stdout.strip()


def dv_token(force=False):
    global _DV_TOKEN
    if _DV_TOKEN and not force:
        return _DV_TOKEN
    p = subprocess.run(["az", "account", "get-access-token", "--resource", DATAVERSE_URL,
                        "--query", "accessToken", "-o", "tsv"], shell=True, text=True, capture_output=True)
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError(f"Failed to acquire Dataverse token: {p.stderr.strip()}")
    _DV_TOKEN = p.stdout.strip()
    return _DV_TOKEN


def dv_request(method, path, body=None):
    tok = dv_token()
    req = urllib.request.Request(
        f"{DATAVERSE_URL}/api/data/v9.2/{path.lstrip('/')}", method=method,
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json",
                 "OData-MaxVersion": "4.0", "OData-Version": "4.0",
                 "Content-Type": "application/json", "Prefer": "return=representation"},
        data=(json.dumps(body).encode() if body is not None else None))
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


def phase_a_entra():
    banner("Phase A: Entra app registration")
    step(f"Find or create app '{APP_DISPLAY_NAME}'")
    existing = json.loads(az("ad", "app", "list", "--display-name", APP_DISPLAY_NAME, "-o", "json"))
    if existing:
        app = existing[0]
        print(f"  reusing appId={app['appId']}")
    else:
        app = json.loads(az("ad", "app", "create", "--display-name", APP_DISPLAY_NAME,
                            "--sign-in-audience", "AzureADMyOrg", "-o", "json"))
        print(f"  created appId={app['appId']}")
    app_id = app["appId"]
    step("Add Dynamics CRM delegated permission")
    az("ad", "app", "permission", "add", "--id", app_id, "--api", DYNAMICS_CRM_APP_ID,
       "--api-permissions", f"{DYNAMICS_CRM_USER_IMPERSONATION_ID}=Scope")
    step("Set Teams platform Web redirect URI")
    az("ad", "app", "update", "--id", app_id, "--web-redirect-uris", TEAMS_PLATFORM_REDIRECT_URI)
    step("Ensure service principal")
    sps = json.loads(az("ad", "sp", "list", "--filter", f"appId eq '{app_id}'", "-o", "json"))
    sp_id = sps[0]["id"] if sps else json.loads(az("ad", "sp", "create", "--id", app_id, "-o", "json"))["id"]
    print(f"  servicePrincipalId={sp_id}")
    step("Attempt admin consent")
    try:
        az("ad", "app", "permission", "admin-consent", "--id", app_id)
        consent = True
        print("  OK  admin consent granted")
    except subprocess.CalledProcessError:
        consent = False
        print("  WARN admin consent failed (need privileged admin); per-user consent at Connect will be required")
        print(f"        az ad app permission admin-consent --id {app_id}")
    step("Create client secret (1 year)")
    blob = json.loads(az("ad", "app", "credential", "reset", "--id", app_id,
                         "--display-name", f"cowork-{DEPLOY_TAG}-{datetime.now(timezone.utc):%Y%m%d}",
                         "--years", "1", "--append", "-o", "json"))
    print(f"  secret created (expires {blob.get('endDateTime')})")
    return {"appId": app_id, "servicePrincipalId": sp_id, "tenantId": blob.get("tenant") or TENANT_ID,
            "clientSecret": blob.get("password"), "secretExpires": blob.get("endDateTime"),
            "adminConsentGranted": consent}


def phase_b_app_user(app_id):
    banner("Phase B: Dataverse application user")
    step(f"Check systemuser for applicationid={app_id}")
    q = urllib.parse.quote(f"applicationid eq {app_id}")
    s, p = dv_request("GET", f"systemusers?$select=systemuserid&$filter={q}")
    if s != 200:
        print(f"  FAIL HTTP {s}: {p}"); sys.exit(1)
    if p.get("value"):
        uid = p["value"][0]["systemuserid"]; print(f"  reusing systemuserid={uid}")
    else:
        step("Create application user")
        s, bu = dv_request("GET", "businessunits?$select=businessunitid&$filter=" +
                           urllib.parse.quote("_parentbusinessunitid_value eq null"))
        if s != 200 or not bu.get("value"):
            print(f"  FAIL root BU: HTTP {s}"); sys.exit(1)
        root = bu["value"][0]["businessunitid"]
        s, c = dv_request("POST", "systemusers", {"applicationid": app_id,
                          "businessunitid@odata.bind": f"/businessunits({root})"})
        if s not in (200, 201, 204):
            print(f"  FAIL HTTP {s}: {c}"); sys.exit(1)
        uid = c.get("systemuserid"); print(f"  created systemuserid={uid}")
    step(f"Assign '{SYSTEM_ADMINISTRATOR_ROLE}'")
    q = urllib.parse.quote(f"name eq '{SYSTEM_ADMINISTRATOR_ROLE}'")
    s, roles = dv_request("GET", f"roles?$select=roleid,_businessunitid_value&$filter={q}")
    if s != 200 or not roles.get("value"):
        print(f"  WARN role not found"); return {"systemUserId": uid, "roleAssigned": False}
    # prefer role in the app user's BU
    s2, urow = dv_request("GET", f"systemusers({uid})?$select=_businessunitid_value")
    ubu = urow.get("_businessunitid_value") if isinstance(urow, dict) else None
    rid = None
    for r in roles["value"]:
        if r.get("_businessunitid_value") == ubu:
            rid = r["roleid"]; break
    if not rid:
        rid = roles["value"][0]["roleid"]
    s, p = dv_request("POST", f"systemusers({uid})/systemuserroles_association/$ref",
                      {"@odata.id": f"{DATAVERSE_URL}/api/data/v9.2/roles({rid})"})
    ok = s in (204, 200, 412)
    print(f"  {'OK' if ok else 'WARN'} role assign status={s}")
    return {"systemUserId": uid, "roleId": rid, "roleAssigned": ok}


def _add_allowlist(app_id):
    for un in (MCP_CLIENT_UNIQUENAME, f"new_{MCP_CLIENT_UNIQUENAME}"):
        s, p = dv_request("POST", "allowedmcpclients",
                          {"name": APP_DISPLAY_NAME, "uniquename": un, "applicationid": app_id, "isenabled": True})
        if s in (200, 201, 204):
            cid = p.get("allowedmcpclientid") if isinstance(p, dict) else None
            print(f"  OK created (uniquename={un}, id={cid})"); return cid
        print(f"  retry uniquename='{un}': HTTP {s}: {p}")
    return None


def phase_d_allowlist(app_id):
    banner("Phase D: MCP allowlist")
    res = {}
    step("Enable built-in 'microsoftcowork'")
    s, p = dv_request("GET", "allowedmcpclients?$select=allowedmcpclientid,isenabled&$filter=" +
                      urllib.parse.quote("uniquename eq 'microsoftcowork'"))
    if s == 200 and p.get("value"):
        row = p["value"][0]
        if not row["isenabled"]:
            dv_request("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
        print(f"  OK microsoftcowork enabled (id={row['allowedmcpclientid']})")
        res["microsoftCoworkId"] = row["allowedmcpclientid"]
    else:
        print("  WARN 'microsoftcowork' row not found (env-level MCP may be off; see RUNBOOK)")
    step(f"Add '{APP_DISPLAY_NAME}' (appId={app_id})")
    s, p = dv_request("GET", "allowedmcpclients?$select=allowedmcpclientid,isenabled&$filter=" +
                      urllib.parse.quote(f"applicationid eq '{app_id}'"))
    if s == 200 and p.get("value"):
        row = p["value"][0]
        if not row["isenabled"]:
            dv_request("PATCH", f"allowedmcpclients({row['allowedmcpclientid']})", {"isenabled": True})
        print(f"  OK existing row (id={row['allowedmcpclientid']})")
        res["myClientId"] = row["allowedmcpclientid"]
    else:
        cid = _add_allowlist(app_id)
        if cid is None:
            print("  FAIL could not add allowed MCP client"); sys.exit(1)
        res["myClientId"] = cid
    return res


def _read_env(path):
    out = {}
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); out[k.strip()] = v.strip()
    return out


def _write_env(path, values, header):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {header}", f"# Managed by {DEPLOY_TAG}/deploy/provision.py.", ""]
    body += [f"{k}={v}" for k, v in values.items()]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _register_yml():
    return (f"version: v1.11\n\nenvironmentFolderPath: ./env\n\nprovision:\n"
            f"  - uses: oauth/register\n    with:\n"
            f"      name: {OAUTH_NAME}\n      flow: authorizationCode\n"
            f"      appId: ${{{{TEAMS_APP_ID}}}}\n      clientId: ${{{{AAD_APP_CLIENT_ID}}}}\n"
            f"      clientSecret: ${{{{SECRET_AAD_APP_CLIENT_SECRET}}}}\n"
            f"      baseUrl: ${{{{DATAVERSE_BASE_URL}}}}\n"
            f"      authorizationUrl: https://login.microsoftonline.com/${{{{TENANT_ID}}}}/oauth2/v2.0/authorize\n"
            f"      tokenUrl: https://login.microsoftonline.com/${{{{TENANT_ID}}}}/oauth2/v2.0/token\n"
            f"      refreshUrl: https://login.microsoftonline.com/${{{{TENANT_ID}}}}/oauth2/v2.0/token\n"
            f"      scope: ${{{{DATAVERSE_OAUTH_SCOPE}}}}\n      identityProvider: Custom\n"
            f"      applicableToApps: AnyApp\n      targetAudience: HomeTenant\n"
            f"    writeToEnvironmentFile:\n      configurationId: {OAUTH_CONFIG_VAR}\n"
            f"projectId: {PROJECT_ID}\n")


def _update_yml():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return (f"version: v1.11\n\nenvironmentFolderPath: ./env\n\nprovision:\n"
            f"  - uses: oauth/update\n    with:\n"
            f"      name: {OAUTH_NAME}-sync-{stamp}\n"
            f"      configurationId: ${{{{{OAUTH_CONFIG_VAR}}}}}\n"
            f"      appId: ${{{{TEAMS_APP_ID}}}}\n      clientId: ${{{{AAD_APP_CLIENT_ID}}}}\n"
            f"      clientSecret: ${{{{SECRET_AAD_APP_CLIENT_SECRET}}}}\n"
            f"      baseUrl: ${{{{DATAVERSE_BASE_URL}}}}\n"
            f"      authorizationUrl: https://login.microsoftonline.com/${{{{TENANT_ID}}}}/oauth2/v2.0/authorize\n"
            f"      tokenUrl: https://login.microsoftonline.com/${{{{TENANT_ID}}}}/oauth2/v2.0/token\n"
            f"      refreshUrl: https://login.microsoftonline.com/${{{{TENANT_ID}}}}/oauth2/v2.0/token\n"
            f"      scope: ${{{{DATAVERSE_OAUTH_SCOPE}}}}\n"
            f"      applicableToApps: SpecificApp\n      targetAudience: HomeTenant\n"
            f"projectId: {PROJECT_ID}\n")


def _redact(t, s):
    return t.replace(s, "***REDACTED***") if (s and t) else t


def phase_e_oauth(entra):
    banner("Phase E: Teams Dev Portal OAuth registration (atk)")
    teams_app_id = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["id"]
    app_id = entra["appId"]; secret = entra.get("clientSecret")
    print(f"  TEAMS_APP_ID={teams_app_id}  AAD_APP_CLIENT_ID={app_id}")
    env_dev = ATK_ENV_DIR / f".env.{ATK_ENV_NAME}"
    env_user = ATK_ENV_DIR / f".env.{ATK_ENV_NAME}.user"
    prior = _read_env(env_dev).get(OAUTH_CONFIG_VAR)
    dev = {"TEAMS_APP_ID": teams_app_id, "AAD_APP_CLIENT_ID": app_id, "TENANT_ID": TENANT_ID,
           "DATAVERSE_BASE_URL": DATAVERSE_URL, "DATAVERSE_MCP_URL": f"{DATAVERSE_URL}{MCP_URL_SUFFIX}",
           "DATAVERSE_OAUTH_SCOPE": f"openid offline_access {DATAVERSE_URL}/.default", "TEAMSFX_ENV": ATK_ENV_NAME}
    if prior:
        dev[OAUTH_CONFIG_VAR] = prior; print("  reusing existing OAuth config id")
    _write_env(env_dev, dev, "atk env (dev) - non-secret")
    _write_env(env_user, {"SECRET_AAD_APP_CLIENT_SECRET": secret or ""}, "atk env (dev) - secrets - DO NOT COMMIT")
    if not (ATK_ENV_DIR / ".gitignore").exists():
        (ATK_ENV_DIR / ".gitignore").write_text("# Secrets stay local.\n.env.*.user\n", encoding="utf-8")
    yml = THIS_DIR / "m365agents.yml"
    yml.write_text(_update_yml() if prior else _register_yml(), encoding="utf-8")
    step(f"atk provision --env {ATK_ENV_NAME} -i false")
    try:
        proc = subprocess.run(["atk", "provision", "--env", ATK_ENV_NAME, "-i", "false"],
                              cwd=str(THIS_DIR), capture_output=True, text=True, shell=True, timeout=180)
    except subprocess.TimeoutExpired:
        print("  FAIL atk timed out"); return {"status": "failed", "reason": "timeout"}
    out = _redact(proc.stdout or "", secret); err = _redact(proc.stderr or "", secret)
    if proc.returncode != 0:
        print(f"  FAIL atk rc={proc.returncode}\n{out}\n{err}")
        return {"status": "failed", "atk_rc": proc.returncode, "atk_stdout": out, "atk_stderr": err}
    for line in out.strip().splitlines()[-8:]:
        print(f"  | {line}")
    after = _read_env(env_dev).get(OAUTH_CONFIG_VAR, "").strip()
    if not after:
        print(f"  FAIL {OAUTH_CONFIG_VAR} missing after provision"); return {"status": "failed", "reason": "no config id"}
    try:
        decoded = base64.b64decode(after).decode("utf-8", errors="replace")
    except Exception:
        decoded = ""
    sep = "###" if "###" in decoded else ("##" if "##" in decoded else "")
    oauth_id = decoded.split(sep, 1)[1] if sep else decoded
    step("OAuth registration result")
    print(f"  referenceId (b64) = {after}")
    print(f"  decoded           = {decoded}")
    return {"status": "ok", "referenceId": after, "oAuthConfigId": oauth_id, "teamsAppId": teams_app_id}


def main():
    banner(f"Provision Cowork plugin: {APP_DISPLAY_NAME}")
    print(f"  Tenant {TENANT_ID}\n  Dataverse {DATAVERSE_URL}\n  Env {ENVIRONMENT_ID}")
    s, who = dv_request("GET", "WhoAmI")
    if s != 200 or not isinstance(who, dict) or who.get("OrganizationId", "").lower() != ORGANIZATION_ID:
        print(f"  FAIL WhoAmI did not confirm org. HTTP {s}: {who}")
        print("        Run `az login` as a user with access to this environment first.")
        return 1
    print(f"  WhoAmI OK user={who.get('UserId')} org={who.get('OrganizationId')}")
    art = {"timestamp": datetime.now(timezone.utc).isoformat(), "tenantId": TENANT_ID,
           "dataverseUrl": DATAVERSE_URL, "environmentId": ENVIRONMENT_ID}
    art["entra"] = phase_a_entra()
    art["dataverse"] = phase_b_app_user(art["entra"]["appId"])
    art["mcpAllowlist"] = phase_d_allowlist(art["entra"]["appId"])
    art["oauth"] = phase_e_oauth(art["entra"])
    out = DEPLOY_DIR / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.write_text(json.dumps(art, indent=2))
    print(f"\n  Wrote artifacts to {out}")
    if art["oauth"].get("status") != "ok":
        banner("Phase E FAILED - see logs above"); return 1
    ref = art["oauth"]["referenceId"]
    banner("Scriptable provisioning complete")
    print(f"""
  [x] Entra app           appId={art['entra']['appId']}
  [x] Dataverse app user  systemuserid={art['dataverse'].get('systemUserId')}
  [x] allowedmcpclients
  [x] Teams OAuth         oAuthConfigId={art['oauth']['oAuthConfigId']}

  referenceId (paste into ../manifest.json, or pass to build.ps1):
    {ref}

  Next:
    cd {PKG_DIR}
    .\\build.ps1 -OAuthReferenceId "{ref}"
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
