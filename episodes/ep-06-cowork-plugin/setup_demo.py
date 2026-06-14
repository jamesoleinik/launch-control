"""Set up the Episode 6 demo end-to-end on the Dataverse side.

What this does (idempotent, safe to re-run):

  1. Verify Dataverse auth (WhoAmI) using scripts/auth.py.
  2. Verify the lc_* tables that the demo prompts depend on.
  3. Seed the curated 'Q3 Widget Launch' demo data so the recording prompts
     return deterministic answers. Delegates to scripts/seed_q3_widget_launch.py.
  4. Final preflight run.

What this does NOT do (no API exists -- must be done in-portal):

  - Create the Entra app registration
  - Add the Allowed MCP Client row in Power Platform admin center
  - Create the Teams Developer Portal OAuth registration
  - Upload the package zip in M365 Admin Center
  - Click "Connect" in Cowork

After auth is good, run from repo root:

    python episodes/ep-06-cowork-plugin/setup_demo.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402


CORE_TABLES = [
    "lc_launch", "lc_milestone", "lc_task",
    "lc_teammember", "lc_statusupdate",
]
DEMO_LAUNCH_NAME = "Q3 Widget Launch"


def banner(msg: str) -> None:
    print()
    print("=" * 72)
    print(f"  {msg}")
    print("=" * 72)


def step(num: int, msg: str) -> None:
    print(f"\n[{num}] {msg}")


def run_subprocess(args: list[str]) -> int:
    print(f"    $ {' '.join(args)}")
    rc = subprocess.call(args, cwd=str(REPO_ROOT))
    return rc


def main() -> int:
    load_env()
    dv_url = os.environ.get("DATAVERSE_URL", "").rstrip("/")
    if not dv_url:
        print("FATAL: DATAVERSE_URL missing from .env")
        return 2

    banner(f"Episode 6 demo setup -> {dv_url}")

    # --- 1. WhoAmI
    step(1, "Dataverse auth (WhoAmI)")
    try:
        import urllib.request, json
        cred = get_credential()
        tok = cred.get_token(f"{dv_url}/.default").token
        req = urllib.request.Request(
            f"{dv_url}/api/data/v9.2/WhoAmI",
            headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            who = json.loads(r.read().decode())
        print(f"    OK  UserId={who.get('UserId')}  OrgId={who.get('OrganizationId')}")
    except Exception as e:
        msg = str(e)
        print(f"    FAIL  {msg.splitlines()[0]}")
        if "AADSTS50076" in msg or "interaction" in msg.lower():
            print()
            print("    -> Run this in a separate terminal, then re-run setup_demo.py:")
            print(f"       az logout")
            print(f"       az login --tenant adfa4542-3e1e-46f5-9c70-3df0b15b3f6c "
                  f"--scope {dv_url}/.default")
        return 1

    # --- 2. Core tables
    step(2, "Core lc_* tables exist")
    try:
        from PowerPlatform.Dataverse.client import DataverseClient
        client = DataverseClient(dv_url, get_credential())
        missing = []
        for t in CORE_TABLES:
            try:
                info = client.tables.get(t)
                if info:
                    print(f"    OK  {t}")
                else:
                    missing.append(t)
                    print(f"    MISSING  {t}")
            except Exception as e:
                missing.append(t)
                print(f"    MISSING  {t}  ({e})")
        if missing:
            print()
            print("    -> Re-run the schema builder:")
            print("       python scripts/build_launchcontrol_schema_fast.py")
            return 1
    except Exception as e:
        print(f"    FAIL  could not load DataverseClient: {e}")
        return 1

    # --- 3. Seed Q3 Widget Launch (import + invoke in-process to avoid
    # WindowsApps python.exe stub issues with subprocess.)
    step(3, f"Seed demo data: {DEMO_LAUNCH_NAME}")
    seed = REPO_ROOT / "scripts" / "seed_q3_widget_launch.py"
    if not seed.exists():
        print(f"    SKIP  seed script not found at {seed}")
    else:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("seed_q3_widget_launch", seed)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "main"):
                mod.main()
            print("    OK  seed completed")
        except SystemExit as e:
            if e.code not in (None, 0):
                print(f"    FAIL  seed exited {e.code}")
                return int(e.code or 1)
            print("    OK  seed completed")
        except Exception as e:
            print(f"    FAIL  seed raised: {e}")
            return 1

    # --- 4. Preflight (in-process)
    step(4, "Preflight (full run)")
    pre = REPO_ROOT / "episodes" / "ep-06-cowork-plugin" / "preflight.py"
    rc = 0
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ep06_preflight", pre)
        mod = importlib.util.module_from_spec(spec)
        sys.argv = [str(pre), "--run"]
        spec.loader.exec_module(mod)
    except SystemExit as e:
        rc = int(e.code or 0)
    except Exception as e:
        print(f"    WARN  preflight raised: {e}")
        rc = 1

    banner("Dataverse-side setup complete")
    print(
        "\nNext (tenant-side, manual, on-camera):\n"
        "  a) Entra app registration (Tenant ID + Client ID + secret + Dynamics CRM perm + admin consent)\n"
        "  b) Power Platform admin center -> environment -> Allowed MCP Client = Entra Client ID\n"
        "  c) Teams Developer Portal -> OAuth registrations -> capture OAuth Registration ID\n"
        "  d) Build package zip:\n"
        "       cd plugins/cowork-dataverse-mcp\n"
        "       ./build.ps1 -DataverseUrl <org URL> -OAuthRegistrationId <id from (c)>\n"
        "  e) M365 Admin Center -> Integrated apps -> Upload custom apps -> out/launch-control-cowork-plugin.zip\n"
        "  f) Cowork -> Add plugin -> Launch Control -> Connect\n"
        "  g) Harden: Teams Dev Portal OAuth registration -> App restrictions -> specific Teams App ID\n"
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())
