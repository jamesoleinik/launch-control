"""Reverse Phases A/B/D/E from deploy.py.

For dry-run / re-recording scenarios. Does NOT touch:
  - Dataverse data (lc_* rows stay)
  - Cowork chat plugin install (per-user, no public API)
  - M365 Admin Center custom-agent upload (manual)
  - Teams Dev Portal OAuth config row itself — atk's bundled CLI has no
    delete-oauth-config command, and the Dev Portal API requires an atk-
    issued token (az tokens are 401/403). Teardown clears the local
    LC_OAUTH_CONFIG_ID so the next deploy.py re-registers cleanly; the
    orphan row in Dev Portal is harmless once the Entra app it points at
    is gone, but accumulates over many cycles. Clean manually at
    https://dev.teams.microsoft.com/ if needed.

Order (reverse of deploy.py main()):
  E. Clear env/.env.dev.LC_OAUTH_CONFIG_ID + wipe env/.env.dev.user
  D. Delete allowedmcpclients row for the appId (leave microsoftcowork enabled)
  B. Delete Dataverse application user
  A. Delete Entra app registration (and its service principal cascades)
  + Archive .deploy/ep-06/*.json into _archive/ for forensics
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.auth import get_credential, load_env  # noqa: E402

EP06_DIR = Path(__file__).resolve().parent
ATK_ENV_DIR = EP06_DIR / "env"
DEPLOY_DIR = REPO_ROOT / ".deploy" / "ep-06"
ARCHIVE_DIR = DEPLOY_DIR / "_archive"
APP_DISPLAY_NAME = "LaunchControl-Cowork-MCP"


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
        # Don't raise — teardown should keep going on per-resource failures.
        print(f"  WARN  az exit {proc.returncode}: {(proc.stderr or proc.stdout).strip()[:300]}")
        return ""
    return proc.stdout.strip()


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


def latest_artifact() -> dict | None:
    files = sorted(DEPLOY_DIR.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text())
    except Exception:
        return None


def find_app_id() -> str | None:
    """Resolve appId from the latest .deploy artifact, falling back to az lookup."""
    art = latest_artifact()
    if art and art.get("entra", {}).get("appId"):
        app_id = art["entra"]["appId"]
        print(f"  appId from latest artifact: {app_id}")
        return app_id
    out = az("ad", "app", "list", "--display-name", APP_DISPLAY_NAME, "-o", "json")
    if not out:
        return None
    apps = json.loads(out)
    if not apps:
        return None
    print(f"  appId resolved via az lookup: {apps[0]['appId']}")
    return apps[0]["appId"]


def phase_e_clear_oauth_env() -> dict:
    banner("Phase E (reverse): clear local OAuth env state")
    env_dev = ATK_ENV_DIR / ".env.dev"
    env_user = ATK_ENV_DIR / ".env.dev.user"
    result = {"clearedConfigId": None, "removedUserFile": False, "removedDevFile": False}

    if env_dev.exists():
        lines = env_dev.read_text(encoding="utf-8").splitlines()
        kept = []
        for line in lines:
            if line.strip().startswith("LC_OAUTH_CONFIG_ID="):
                result["clearedConfigId"] = line.split("=", 1)[1].strip()
                print(f"  removed LC_OAUTH_CONFIG_ID={result['clearedConfigId'][:40]}…")
                continue
            kept.append(line)
        env_dev.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
        print(f"  rewrote {env_dev.relative_to(REPO_ROOT)} (kept {len(kept)} lines)")
        result["removedDevFile"] = False  # kept, just edited
    else:
        print(f"  {env_dev.relative_to(REPO_ROOT)} not present")

    if env_user.exists():
        env_user.unlink()
        result["removedUserFile"] = True
        print(f"  deleted {env_user.relative_to(REPO_ROOT)}")
    else:
        print(f"  {env_user.relative_to(REPO_ROOT)} not present")

    print()
    print("  NOTE  Dev Portal OAuth registration is NOT auto-deleted.")
    print("        Once the Entra app is gone the orphan is non-functional,")
    print("        but to keep dev.teams.microsoft.com tidy delete it manually:")
    print("        https://dev.teams.microsoft.com/tools/oauth-configurations")
    return result


def phase_d_remove_allowlist(app_id: str) -> dict:
    banner("Phase D (reverse): remove allowedmcpclients row for our app")
    if not app_id:
        print("  SKIP  no appId resolved")
        return {"skipped": True}
    q = urllib.parse.quote(f"applicationid eq '{app_id}'")
    s, payload = dv_request(
        "GET",
        f"allowedmcpclients?$select=allowedmcpclientid,name&$filter={q}",
    )
    if s != 200 or not payload.get("value"):
        print(f"  no matching row (HTTP {s})")
        return {"deleted": False, "found": False}
    rows = payload["value"]
    deleted: list[str] = []
    for row in rows:
        rid = row["allowedmcpclientid"]
        s, _ = dv_request("DELETE", f"allowedmcpclients({rid})")
        if s in (200, 204):
            print(f"  OK  deleted {row['name']} (id={rid})")
            deleted.append(rid)
        else:
            print(f"  WARN  HTTP {s} deleting {rid}")
    return {"deleted": True, "ids": deleted}


def phase_b_remove_app_user(app_id: str) -> dict:
    banner("Phase B (reverse): remove Dataverse Application User")
    if not app_id:
        print("  SKIP  no appId resolved")
        return {"skipped": True}
    q = urllib.parse.quote(f"applicationid eq {app_id}")
    s, payload = dv_request(
        "GET",
        f"systemusers?$select=systemuserid,fullname&$filter={q}",
    )
    if s != 200 or not payload.get("value"):
        print(f"  no matching systemuser (HTTP {s})")
        return {"deleted": False, "found": False}
    uid = payload["value"][0]["systemuserid"]
    # Disable first (Dataverse blocks hard-delete of systemusers; that's fine for a re-record).
    s, body = dv_request("PATCH", f"systemusers({uid})", {"isdisabled": True})
    if s in (200, 204):
        print(f"  OK  disabled systemuser {uid}")
        return {"deleted": False, "disabled": True, "id": uid}
    print(f"  WARN  HTTP {s} disabling {uid}: {body}")
    return {"deleted": False, "disabled": False, "id": uid}


def phase_a_remove_entra(app_id: str | None) -> dict:
    banner("Phase A (reverse): delete Entra app registration")
    if not app_id:
        print("  SKIP  no appId resolved")
        return {"skipped": True}
    az("ad", "app", "delete", "--id", app_id)
    # Verify
    out = az("ad", "app", "show", "--id", app_id, "-o", "json")
    if out == "":
        print(f"  OK  app {app_id} deleted (or already gone)")
        return {"deleted": True, "appId": app_id}
    print(f"  WARN  app {app_id} still resolvable after delete")
    return {"deleted": False, "appId": app_id}


def archive_deploy_artifacts() -> int:
    banner("Archive .deploy/ep-06/*.json")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    moved = 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for p in DEPLOY_DIR.glob("*.json"):
        dest = ARCHIVE_DIR / f"{stamp}__{p.name}"
        shutil.move(str(p), dest)
        print(f"  {p.name} -> _archive/{dest.name}")
        moved += 1
    if moved == 0:
        print("  no artifacts to archive")
    return moved


def main() -> int:
    banner("Episode 6 teardown -- reverse Phases A/B/D/E")
    load_env()
    print(f"  Dataverse env: {os.environ.get('DATAVERSE_URL', '?')}")

    app_id = find_app_id()
    if not app_id:
        print("  NOTE  no appId resolvable. Skipping Phases A/B/D; running E + archive only.")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "appId": app_id,
        "phaseE": phase_e_clear_oauth_env(),
        "phaseD": phase_d_remove_allowlist(app_id) if app_id else {"skipped": True},
        "phaseB": phase_b_remove_app_user(app_id) if app_id else {"skipped": True},
        "phaseA": phase_a_remove_entra(app_id),
        "archived": archive_deploy_artifacts(),
    }

    banner("Teardown complete")
    print(json.dumps(results, indent=2, default=str))
    print(
        "\nNext: re-run from a clean slate:\n"
        "  python episodes/ep-06-cowork-plugin/deploy.py\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
