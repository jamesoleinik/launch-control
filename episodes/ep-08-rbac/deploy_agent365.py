"""Episode 8 — recreate the Cowork plugin substrate for the NEW environment.

Re-platforms the Episode 6 plugin (the v1.5.2 lineage, now bumped to v1.6.0)
onto the agent365003 tenant / `org1077ae7c` environment without disturbing the
original `org40ae6a46` wiring. It reuses Episode 6's proven phase functions
(`deploy.py`) but overrides the module-level constants so:

  * a NEW Entra app is minted (`LaunchControl-Cowork-MCP-agent365`),
  * the OAuth registration's `applicableToApps` pins to the NEW plugin manifest
    (`plugins/dataverse-launchcontrol-agent365/manifest.json`), and
  * the atk project state lives in `episodes/ep-08-rbac/atk/` (fresh register,
    not the old env's reused `LC_OAUTH_CONFIG_ID`).

Phases A/B/D/E run end-to-end; Phase C (the legacy package build) is skipped in
favour of zipping the new plugin folder directly with the real `referenceId`.

Prereqs (interactive, done out-of-band):
  * `az login` to the new tenant as a Dataverse System Administrator.
  * `atk account login m365` to the new tenant.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EP08_DIR = Path(__file__).resolve().parent
REPO_ROOT = EP08_DIR.parents[1]
EP06_DEPLOY = REPO_ROOT / "episodes" / "ep-06-cowork-plugin" / "deploy.py"
NEW_PLUGIN_DIR = REPO_ROOT / "plugins" / "dataverse-launchcontrol-agent365"
NEW_PLUGIN_MANIFEST = NEW_PLUGIN_DIR / "manifest.json"
NEW_PLUGIN_ZIP = REPO_ROOT / "plugins" / "dataverse-launchcontrol-agent365.zip"
ATK_DIR = EP08_DIR / "atk"
ATK_ENV_DIR = ATK_DIR / "env"
DEPLOY_DIR = REPO_ROOT / ".deploy" / "ep-08"

APP_DISPLAY_NAME = "LaunchControl-Cowork-MCP-agent365"

OAUTH_REGISTER_YML = """\
version: v1.11

environmentFolderPath: ./env

provision:
  - uses: oauth/register
    with:
      name: LaunchControl-Cowork-OAuth-agent365
      flow: authorizationCode
      appId: ${{TEAMS_APP_ID}}
      clientId: ${{AAD_APP_CLIENT_ID}}
      clientSecret: ${{SECRET_AAD_APP_CLIENT_SECRET}}
      baseUrl: ${{DATAVERSE_MCP_URL}}
      authorizationUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/authorize
      tokenUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token
      refreshUrl: https://login.microsoftonline.com/${{TENANT_ID}}/oauth2/v2.0/token
      scope: ${{DATAVERSE_OAUTH_SCOPE}}
      identityProvider: Custom
      applicableToApps: AnyApp
      targetAudience: HomeTenant
    writeToEnvironmentFile:
      configurationId: LC_OAUTH_CONFIG_ID
"""


def _load_ep06_deploy():
    spec = importlib.util.spec_from_file_location("ep06_deploy", EP06_DEPLOY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _prepare_atk_project():
    ATK_ENV_DIR.mkdir(parents=True, exist_ok=True)
    (ATK_DIR / "m365agents.yml").write_text(OAUTH_REGISTER_YML, encoding="utf-8")
    gi = ATK_ENV_DIR / ".gitignore"
    if not gi.exists():
        gi.write_text("# atk-managed env files. Secrets stay local.\n.env.*.user\n", encoding="utf-8")
    # Start clean: no reused LC_OAUTH_CONFIG_ID so atk registers fresh.
    for f in (".env.dev", ".env.dev.user"):
        p = ATK_ENV_DIR / f
        if p.exists():
            p.unlink()


def _write_reference_id(reference_id: str) -> None:
    data = json.loads(NEW_PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    conn = data["agentConnectors"][0]["toolSource"]["remoteMcpServer"]
    conn["authorization"]["referenceId"] = reference_id
    NEW_PLUGIN_MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  manifest referenceId set -> {reference_id[:24]}...")


def _zip_plugin() -> None:
    files = []
    for p in sorted(NEW_PLUGIN_DIR.rglob("*")):
        if p.is_file():
            files.append(p)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(NEW_PLUGIN_DIR).as_posix())
    NEW_PLUGIN_ZIP.write_bytes(buf.getvalue())
    print(f"  wrote {NEW_PLUGIN_ZIP.relative_to(REPO_ROOT)} ({len(files)} files)")


def main() -> int:
    dep = _load_ep06_deploy()

    # Override the module constants so all phases target the new env/app/plugin.
    dep.APP_DISPLAY_NAME = APP_DISPLAY_NAME
    dep.LIVE_MANIFEST = NEW_PLUGIN_MANIFEST
    dep.ATK_PROJECT_DIR = ATK_DIR
    dep.ATK_ENV_DIR = ATK_ENV_DIR
    dep.ATK_ENV_NAME = "dev"
    dep.DEPLOY_DIR = DEPLOY_DIR
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

    dep.banner("Episode 8 -- recreate Cowork plugin for org1077ae7c (agent365003)")
    dep.load_env()
    print(f"  Dataverse env: {dep.os.environ.get('DATAVERSE_URL')}")
    print(f"  App display:   {APP_DISPLAY_NAME}")
    print(f"  Live manifest: {NEW_PLUGIN_MANIFEST.relative_to(REPO_ROOT)}")

    _prepare_atk_project()

    artifacts = {"timestamp": datetime.now(timezone.utc).isoformat(),
                 "dataverseUrl": dep.os.environ.get("DATAVERSE_URL", "")}
    artifacts["entra"] = dep.phase_a_entra_app()
    artifacts["dataverse"] = dep.phase_b_dataverse_app_user(artifacts["entra"]["appId"])
    artifacts["mcpAllowlist"] = dep.phase_d_mcp_allowlist(artifacts["entra"]["appId"])
    artifacts["oauth"] = dep.phase_e_atk_oauth(artifacts["entra"])

    if artifacts["oauth"].get("status") == "ok":
        _write_reference_id(artifacts["oauth"]["referenceId"])
        _zip_plugin()
    else:
        dep.banner("Phase E (atk oauth/register) FAILED -- manifest referenceId left pending")

    out_path = DEPLOY_DIR / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out_path.write_text(json.dumps(artifacts, indent=2))
    print(f"\n  Wrote artifacts to {out_path.relative_to(REPO_ROOT)}")
    print(f"  Entra appId = {artifacts['entra']['appId']}")
    return 0 if artifacts["oauth"].get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
