"""Local test harness for Episode 8 — The Code-First Agent.

Mirrors the Ep 7 pattern: pre-flight checks on the substrate, plus an
optional live sanity check against Dataverse.

Usage:
    python scripts/test_ep8_locally.py            # P1-P7 only (no network)
    python scripts/test_ep8_locally.py --live     # also runs S1 (live skill sync)

Pre-flights (no network):
  P1: agents/launch-coordinator-py/agent.py imports cleanly
  P2: agents/launch-coordinator-py/sync_skills.py exposes a callable sync()
  P3: agent.py references ./.skills/launch-readiness-checklist.md
      (skills-as-brain literal - the agent's instructions read from this file)
  P4: agent.py registers the Dataverse MCP server with the right command shape
      (npx + @microsoft/dataverse + mcp)
  P5: agent.py registers PermissionHandler.approve_all (the auto-approve gotcha
      that we hit while building the agent)
  P6: requirements.txt pins the right packages
      (agent-framework-github-copilot, rich, python-dotenv, requests)
  P7: agents/launch-coordinator-py/.skills/ is in .gitignore (cache must not
      be committed)

Live (--live):
  S1: sync_skills.sync() runs against the configured Dataverse environment
      and writes >= 1 skill markdown file.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO_ROOT / "agents" / "launch-coordinator-py"
AGENT_PY = AGENT_DIR / "agent.py"
SYNC_PY = AGENT_DIR / "sync_skills.py"
REQS = AGENT_DIR / "requirements.txt"
GITIGNORE = REPO_ROOT / ".gitignore"

# Make `from scripts.auth import ...` and the agent's siblings importable.
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(AGENT_DIR))


# ---------- Tiny pass/fail framework ----------

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
SKIP = "\033[33mSKIP\033[0m"
results: list[tuple[str, str, str]] = []  # (id, name, status)


def check(test_id: str, name: str, fn) -> bool:
    """Run a check function. fn returns (ok: bool, detail: str)."""
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"exception: {exc!r}"
    status = PASS if ok else FAIL
    results.append((test_id, name, status))
    print(f"  [{status}] {test_id}: {name}")
    if detail:
        print(f"         {detail}")
    return ok


# ---------- Pre-flights ----------

def p1_agent_imports() -> tuple[bool, str]:
    if not AGENT_PY.exists():
        return False, f"missing: {AGENT_PY}"
    spec = importlib.util.spec_from_file_location("ep8_agent", AGENT_PY)
    if spec is None or spec.loader is None:
        return False, "could not build import spec"
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001
        return False, f"import failed: {exc!r}"
    needed = ["run_once", "build_mcp_servers", "auto_approve", "INSTRUCTIONS",
              "SKILLS_DIR"]
    missing = [n for n in needed if not hasattr(mod, n)]
    if missing:
        return False, f"missing attributes: {missing}"
    return True, f"loaded with {len(needed)} expected symbols"


def p2_sync_skills_callable() -> tuple[bool, str]:
    if not SYNC_PY.exists():
        return False, f"missing: {SYNC_PY}"
    spec = importlib.util.spec_from_file_location("ep8_sync", SYNC_PY)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    if not hasattr(mod, "sync") or not callable(mod.sync):
        return False, "sync_skills.sync is not callable"
    return True, "sync_skills.sync(target_dir) is callable"


def p3_skill_load_literal() -> tuple[bool, str]:
    text = AGENT_PY.read_text(encoding="utf-8")
    literal = "./.skills/launch-readiness-checklist.md"
    if literal not in text:
        return False, f"agent.py does not reference {literal!r}"
    return True, f"found skills-as-brain literal: {literal}"


def p4_mcp_wiring() -> tuple[bool, str]:
    text = AGENT_PY.read_text(encoding="utf-8")
    needed = ["mcp_servers", '"dataverse"', "@microsoft/dataverse", '"mcp"']
    missing = [m for m in needed if m not in text]
    if missing:
        return False, f"missing tokens: {missing}"
    return True, "Dataverse MCP server registered"


def p5_permission_handler() -> tuple[bool, str]:
    text = AGENT_PY.read_text(encoding="utf-8")
    if "PermissionHandler.approve_all" not in text:
        return False, "PermissionHandler.approve_all not registered (the gotcha)"
    if "on_permission_request" not in text:
        return False, "on_permission_request not registered with the agent"
    return True, "auto-approve permission handler registered"


def p6_requirements() -> tuple[bool, str]:
    if not REQS.exists():
        return False, f"missing: {REQS}"
    text = REQS.read_text(encoding="utf-8")
    needed = ["agent-framework-github-copilot", "rich", "python-dotenv", "requests"]
    missing = [n for n in needed if n not in text]
    if missing:
        return False, f"requirements.txt missing pins: {missing}"
    return True, "requirements.txt pins all expected packages"


def p7_gitignore() -> tuple[bool, str]:
    if not GITIGNORE.exists():
        return False, f"missing: {GITIGNORE}"
    text = GITIGNORE.read_text(encoding="utf-8")
    needle = "agents/launch-coordinator-py/.skills"
    if needle not in text:
        return False, f".gitignore does not exclude {needle}"
    return True, f"skills cache is gitignored ({needle})"


# ---------- Live ----------

def s1_live_skill_sync() -> tuple[bool, str]:
    spec = importlib.util.spec_from_file_location("ep8_sync_live", SYNC_PY)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    target = AGENT_DIR / ".skills"
    written = mod.sync(target)
    if not written:
        return False, "sync() returned 0 skills - is .env wired up?"
    names = [s["name"] for s in written]
    return True, f"synced {len(written)} skills: {names}"


# ---------- Driver ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true",
                    help="Also run S1 (live skill sync against Dataverse)")
    args = ap.parse_args()

    print("Episode 8 pre-flight")
    print("====================\n")
    print("Pre-flights (no network):")
    check("P1", "agent.py imports cleanly", p1_agent_imports)
    check("P2", "sync_skills.sync is callable", p2_sync_skills_callable)
    check("P3", "agent.py references skills-as-brain literal", p3_skill_load_literal)
    check("P4", "Dataverse MCP server wired in", p4_mcp_wiring)
    check("P5", "PermissionHandler.approve_all registered", p5_permission_handler)
    check("P6", "requirements.txt pins expected packages", p6_requirements)
    check("P7", "skills cache is gitignored", p7_gitignore)

    if args.live:
        print("\nLive sanity check:")
        check("S1", "sync_skills.sync() returns >= 1 skill", s1_live_skill_sync)

    print("\nSummary")
    print("-------")
    failed = [r for r in results if FAIL in r[2]]
    print(f"  total: {len(results)}   pass: {len(results) - len(failed)}   "
          f"fail: {len(failed)}")
    if failed:
        for tid, name, _ in failed:
            print(f"    - {tid}: {name}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
