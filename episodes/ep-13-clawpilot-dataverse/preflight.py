"""Local test harness for Episode 13 - Clawpilot + Dataverse.

Read-only checks for the recording substrate.

Usage:
    python episodes/ep-13-clawpilot-dataverse/preflight.py
    python episodes/ep-13-clawpilot-dataverse/preflight.py --offline
    python episodes/ep-13-clawpilot-dataverse/preflight.py --copilot-home C:\\Users\\me\\.copilot

Checks:
  P1: .env and scripts/auth.py exist; DATAVERSE_URL can be loaded.
  P2: Dataverse MCP URL can be derived from DATAVERSE_URL.
  P3: Clawpilot.exe and/or the `copilot` CLI are installed.
  P4: ~/.copilot/ substrate exists with mcp-config.json + installed-plugins/ + skills/.
  P5: ~/.copilot/mcp-config.json has a Dataverse MCP entry matching DATAVERSE_URL.
  P6: The awesome-copilot/dataverse plugin is installed locally.
  S1: Live read-only auth probe reaches the Dataverse MCP endpoint.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUTH_PY = REPO_ROOT / "scripts" / "auth.py"
ENV_FILE = REPO_ROOT / ".env"

sys.path.insert(0, str(REPO_ROOT))


# ---------- Color (Windows-friendly) ----------

class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    END = "\033[0m"


if os.name == "nt":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        for key in dir(C):
            if not key.startswith("_"):
                setattr(C, key, "")


PASS = C.GREEN + " OK " + C.END
FAIL = C.RED + "FAIL" + C.END
SKIP = C.YELLOW + "SKIP" + C.END

results: list[tuple[str, str, str, str, int]] = []
state: dict[str, str] = {}


# ---------- Helpers ----------


def timed_check(test_id: str, name: str, fn) -> bool:
    t0 = time.time()
    try:
        ok, detail = fn()
        status = PASS if ok else FAIL
    except Exception as exc:  # noqa: BLE001
        ok = False
        status = FAIL
        detail = f"exception: {exc!r}"
    elapsed_ms = int((time.time() - t0) * 1000)
    results.append((test_id, name, status, detail, elapsed_ms))
    print(f"  [{status}] {test_id}: {name}  {C.DIM}({elapsed_ms}ms){C.END}")
    if detail:
        print(f"         {C.DIM}{detail}{C.END}")
    return ok


def skip_check(test_id: str, name: str, detail: str) -> None:
    results.append((test_id, name, SKIP, detail, 0))
    print(f"  [{SKIP}] {test_id}: {name}")
    print(f"         {C.DIM}{detail}{C.END}")


def load_dotenv_minimal(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def import_auth_module():
    if not AUTH_PY.exists():
        return None
    spec = importlib.util.spec_from_file_location("launch_control_auth", AUTH_PY)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def home_candidates() -> list[Path]:
    """Return likely user-home roots, skipping OneDrive-redirected ones.

    On corporate Windows boxes USERPROFILE is sometimes redirected into a
    OneDrive subfolder, but the `~/.copilot/` substrate is always under the
    real `C:\\Users\\<name>` path. Prefer that, fall back to env vars.
    """
    candidates: list[Path] = []
    drive = os.environ.get("HOMEDRIVE")
    name = os.environ.get("USERNAME") or os.environ.get("USER")
    if drive and name:
        candidates.append(Path(drive + "\\Users\\" + name))
    for raw in (os.environ.get("USERPROFILE"), os.environ.get("HOME")):
        if raw:
            candidates.append(Path(raw))
    drive2 = os.environ.get("HOMEDRIVE")
    path = os.environ.get("HOMEPATH")
    if drive2 and path:
        candidates.append(Path(drive2 + path))
    candidates.append(Path.home())
    unique: list[Path] = []
    seen: set[str] = set()
    for home in candidates:
        key = str(home).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(home)
    return unique


def find_copilot_home(override: Path | None) -> Path | None:
    if override:
        return override if override.exists() else None
    env_override = os.environ.get("COPILOT_HOME")
    if env_override:
        candidate = Path(env_override)
        if candidate.exists():
            return candidate
    for home in home_candidates():
        candidate = home / ".copilot"
        if candidate.exists():
            return candidate
    return None


def find_clawpilot_exe() -> Path | None:
    for home in home_candidates():
        for sub in (
            home / "AppData" / "Local" / "Programs" / "clawpilot" / "Clawpilot.exe",
            home / "AppData" / "Local" / "Programs" / "Clawpilot" / "Clawpilot.exe",
        ):
            if sub.exists():
                return sub
    return None


def find_copilot_cli() -> str | None:
    found = shutil.which("copilot")
    if found:
        return found
    for home in home_candidates():
        for sub in (
            home / "AppData" / "Roaming" / "Code" / "User" / "globalStorage"
                  / "github.copilot-chat" / "copilotCli" / "copilot.ps1",
            home / "AppData" / "Roaming" / "npm" / "copilot.cmd",
            home / "AppData" / "Roaming" / "npm" / "copilot",
        ):
            if sub.exists():
                return str(sub)
    return None


def url_host(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    return (parsed.netloc or parsed.path).lower().rstrip("/")


# ---------- Checks ----------


def p1_env_and_auth() -> tuple[bool, str]:
    if not ENV_FILE.exists():
        return False, f"missing {ENV_FILE}"
    if not AUTH_PY.exists():
        return False, f"missing {AUTH_PY}"

    load_dotenv_minimal(ENV_FILE)
    try:
        auth = import_auth_module()
        if auth is not None and hasattr(auth, "load_env"):
            auth.load_env()
    except Exception as exc:  # noqa: BLE001
        return False, f"scripts/auth.py load failed: {exc!r}"

    env_url = os.environ.get("DATAVERSE_URL", "").strip().rstrip("/")
    if not env_url:
        return False, "DATAVERSE_URL is not set"
    parsed = urllib.parse.urlparse(env_url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False, f"DATAVERSE_URL is not an https URL: {env_url}"
    state["dataverse_url"] = env_url
    state["dataverse_host"] = parsed.netloc.lower()
    return True, env_url


def p2_mcp_url() -> tuple[bool, str]:
    env_url = state.get("dataverse_url") or os.environ.get("DATAVERSE_URL", "").rstrip("/")
    if not env_url:
        return False, "P1 did not resolve DATAVERSE_URL"
    mcp_url = env_url + "/api/mcp"
    mcp_url_preview = env_url + "/api/mcp_preview"
    state["mcp_url"] = mcp_url
    state["mcp_url_preview"] = mcp_url_preview
    return True, f"{mcp_url}  (or preview: {mcp_url_preview})"


def p3_clawpilot_and_cli() -> tuple[bool, str]:
    exe = find_clawpilot_exe()
    cli = find_copilot_cli()
    parts: list[str] = []
    if exe:
        parts.append(f"Clawpilot.exe={exe}")
        state["clawpilot_exe"] = str(exe)
    if cli:
        parts.append(f"copilot={cli}")
        state["copilot_cli"] = cli
    if not parts:
        return False, "neither Clawpilot.exe nor the `copilot` CLI was found"
    if not exe:
        parts.append("(no Clawpilot.exe — desktop client not installed)")
    if not cli:
        parts.append("(no `copilot` CLI — install with `npm install -g @github/copilot`)")
    return True, "; ".join(parts)


def p4_copilot_home(copilot_home: Path | None) -> tuple[bool, str]:
    home = copilot_home or find_copilot_home(None)
    if home is None:
        return False, "no ~/.copilot/ found; install GitHub Copilot CLI or launch Clawpilot once"
    state["copilot_home"] = str(home)
    missing: list[str] = []
    for child in ("mcp-config.json", "installed-plugins", "skills"):
        if not (home / child).exists():
            missing.append(child)
    if missing:
        return False, f"{home}: missing {', '.join(missing)}"
    return True, f"{home} (mcp-config.json + installed-plugins/ + skills/ present)"


def p5_mcp_entry_for_env() -> tuple[bool, str]:
    home_str = state.get("copilot_home")
    host = state.get("dataverse_host")
    if not home_str:
        return False, "P4 did not locate ~/.copilot/"
    if not host:
        return False, "P1 did not resolve DATAVERSE_URL host"

    config_path = Path(home_str) / "mcp-config.json"
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        return False, f"cannot read {config_path}: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return False, f"{config_path} is not valid JSON: {exc}"

    servers = data.get("mcpServers") or {}
    matches: list[str] = []
    for name, entry in servers.items():
        url = (entry or {}).get("url", "")
        if not url:
            continue
        if url_host(url) == host:
            path = urllib.parse.urlparse(url).path or ""
            matches.append(f"{name} -> {path or '/'}")

    if not matches:
        sample = ", ".join(servers.keys()) or "(none)"
        return False, (
            f"no MCP server in {config_path.name} matches host {host}; "
            f"servers present: {sample}"
        )
    return True, f"{len(matches)} match(es): " + "; ".join(matches[:3])


def p6_dataverse_plugin() -> tuple[bool, str]:
    home_str = state.get("copilot_home")
    if not home_str:
        return False, "P4 did not locate ~/.copilot/"
    home = Path(home_str)
    candidates = [
        home / "installed-plugins" / "awesome-copilot" / "dataverse",
        home / "installed-plugins" / "microsoft" / "dataverse",
    ]
    for plugin_root in candidates:
        if plugin_root.exists():
            skill_files = list((plugin_root / "skills").glob("*/SKILL.md")) if (plugin_root / "skills").exists() else []
            plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
            detail = f"{plugin_root}: {len(skill_files)} SKILL.md file(s)"
            if plugin_json.exists():
                try:
                    meta = json.loads(plugin_json.read_text(encoding="utf-8"))
                    detail += f"; plugin {meta.get('name', '?')}@{meta.get('version', '?')}"
                except (OSError, json.JSONDecodeError):
                    pass
            state["dataverse_plugin_root"] = str(plugin_root)
            return True, detail
    return False, (
        "awesome-copilot/dataverse plugin not installed under "
        "~/.copilot/installed-plugins/ - install via `copilot plugin install` "
        "or rerun dv-connect"
    )


def s1_mcp_reachable() -> tuple[bool, str]:
    candidates = [u for u in (state.get("mcp_url"), state.get("mcp_url_preview")) if u]
    if not candidates:
        return False, "P2 did not derive an MCP URL"
    auth = import_auth_module()
    if auth is None or not hasattr(auth, "get_token"):
        return False, "scripts/auth.py does not expose get_token()"
    token = auth.get_token()

    last_detail = ""
    for mcp_url in candidates:
        req = urllib.request.Request(mcp_url, method="GET")
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read(512).decode("utf-8", errors="replace")
                return True, f"{mcp_url} -> HTTP {resp.status}; {body[:120]}"
        except urllib.error.HTTPError as exc:
            body = exc.read(512).decode("utf-8", errors="replace")
            if exc.code in (400, 405, 406, 415):
                return True, f"{mcp_url} -> HTTP {exc.code} (GET rejected as expected); {body[:120]}"
            last_detail = f"{mcp_url} -> HTTP {exc.code}: {body[:200]}"
        except urllib.error.URLError as exc:
            last_detail = f"{mcp_url} -> network error: {exc.reason!r}"
    return False, last_detail or "no MCP endpoint reachable"


# ---------- Driver ----------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip S1 live Dataverse MCP connectivity probe",
    )
    parser.add_argument(
        "--copilot-home",
        default=None,
        help="Override ~/.copilot/ location (default: auto-detect)",
    )
    args = parser.parse_args()

    copilot_home = Path(args.copilot_home).expanduser() if args.copilot_home else None

    print(C.BOLD + "Episode 13 pre-flight - Clawpilot + Dataverse" + C.END)
    print("=" * 60)
    print("Pre-flights:")
    timed_check("P1", ".env + scripts/auth.py + DATAVERSE_URL", p1_env_and_auth)
    timed_check("P2", "Dataverse MCP URL derivable", p2_mcp_url)
    timed_check("P3", "Clawpilot.exe and/or `copilot` CLI installed", p3_clawpilot_and_cli)
    timed_check("P4", "~/.copilot/ substrate present", lambda: p4_copilot_home(copilot_home))
    timed_check("P5", "mcp-config.json has Dataverse entry for this env", p5_mcp_entry_for_env)
    timed_check("P6", "awesome-copilot/dataverse plugin installed", p6_dataverse_plugin)

    if args.offline:
        skip_check("S1", "Dataverse MCP endpoint reachable", "--offline specified")
    else:
        print("\nLive read-only probe:")
        timed_check("S1", "Dataverse MCP endpoint reachable", s1_mcp_reachable)

    failed = [row for row in results if row[2] == FAIL]
    skipped = [row for row in results if row[2] == SKIP]
    passed = len(results) - len(failed) - len(skipped)

    print("\nSummary")
    print("-------")
    print(f"  total: {len(results)}   pass: {passed}   fail: {len(failed)}   skip: {len(skipped)}")
    if failed:
        print("\nRecording is not ready:")
        for test_id, name, _, detail, _ in failed:
            print(f"  - {test_id}: {name} - {detail}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
