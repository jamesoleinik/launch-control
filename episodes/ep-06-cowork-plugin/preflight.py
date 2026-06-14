#!/usr/bin/env python3
"""Read-only local preflight for Episode 6 - Cowork Plugin for Dataverse."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
AUTH_PATH = ROOT / "scripts" / "auth.py"
BUSINESS_SKILLS = ROOT / "business-skills"
PLUGIN_CANDIDATE_DIRS = [
    ROOT / "connectors" / "cowork-dataverse-mcp",
    ROOT / "connectors" / "cowork-launch-control",
    ROOT / "plugins" / "cowork-dataverse-mcp",
    ROOT / "agents" / "cowork-launch-control",
]
CORE_TABLES = ["lc_launch", "lc_milestone", "lc_task", "lc_teammember", "lc_statusupdate"]


PLAN = """# Episode 6 - Cowork Plugin for Dataverse preflight

Read-only checks before recording:

1. Local repo setup
   - `.env` exists and has `DATAVERSE_URL`.
   - `scripts/auth.py` exists and exposes `load_env()` / `get_token()`.
2. Business Skill
   - A Cowork / Dataverse MCP schema-aware skill exists in `business-skills/`.
   - The skill mentions core Launch Control tables, lookup relationships, status fields, and readiness rules.
3. Cowork plugin package
   - A package/scaffold exists under `connectors/`, `plugins/`, or `agents/`.
   - The package contains a manifest and an action/config file.
   - The action/config points at `/api/mcp_preview`, uses `OAuthPluginVault`, and carries a `referenceId`.
4. Dataverse smoke tests
   - `WhoAmI` works through `scripts/auth.py`.
   - Core `lc_*` table metadata exists.

The harness does not create records, upload packages, deploy plugins, or call Cowork.
"""


class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


class Result:
    def __init__(self, name):
        self.name = name
        self.passed = None
        self.detail = ""
        self.elapsed_ms = 0
        self.payload = None

    def ok(self, detail="", payload=None):
        self.passed = True
        self.detail = detail
        self.payload = payload
        return self

    def fail(self, detail="", payload=None):
        self.passed = False
        self.detail = detail
        self.payload = payload
        return self


def _read_dotenv():
    values = {}
    if not ENV_FILE.exists():
        return values
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _dataverse_url():
    value = os.environ.get("DATAVERSE_URL") or os.environ.get("DATAVERSE_ENVIRONMENT_URL")
    if value:
        return value.rstrip("/")
    env_values = _read_dotenv()
    value = env_values.get("DATAVERSE_URL") or env_values.get("DATAVERSE_ENVIRONMENT_URL")
    return value.rstrip("/") if value else ""


def _load_auth_module():
    if not AUTH_PATH.exists():
        raise FileNotFoundError(f"missing {AUTH_PATH}")
    spec = importlib.util.spec_from_file_location("launch_control_auth", AUTH_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import {AUTH_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _token():
    mod = _load_auth_module()
    if hasattr(mod, "load_env"):
        mod.load_env()
    if not hasattr(mod, "get_token"):
        raise RuntimeError("scripts/auth.py does not expose get_token()")
    return mod.get_token()


def _req(method, path, body=None):
    env = _dataverse_url()
    if not env:
        raise RuntimeError("DATAVERSE_URL is not set")
    url = env + "/api/data/v9.2/" + path.lstrip("/")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + _token())
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            text = resp.read().decode("utf-8")
            elapsed_ms = int((time.time() - t0) * 1000)
            return resp.status, (json.loads(text) if text else {}), elapsed_ms
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        elapsed_ms = int((time.time() - t0) * 1000)
        try:
            payload = json.loads(text) if text else {}
        except json.JSONDecodeError:
            payload = {"raw": text}
        return e.code, payload, elapsed_ms


def _json_files(base):
    if not base.exists():
        return []
    return [p for p in base.rglob("*.json") if p.is_file()]


def _text_files(base):
    if not base.exists():
        return []
    wanted = {".json", ".md", ".txt", ".yml", ".yaml"}
    return [p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in wanted]


def _rel(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def preflight_p1():
    r = Result("P1: Local auth substrate")
    t0 = time.time()
    env = _dataverse_url()
    details = []
    ok = True
    if ENV_FILE.exists():
        details.append(".env present")
    else:
        details.append("missing .env")
        ok = False
    if AUTH_PATH.exists():
        details.append("scripts/auth.py present")
    else:
        details.append("missing scripts/auth.py")
        ok = False
    if env:
        details.append(f"DATAVERSE_URL={env}")
    else:
        details.append("missing DATAVERSE_URL")
        ok = False
    r.elapsed_ms = int((time.time() - t0) * 1000)
    return r.ok("; ".join(details), {"dataverse_url": env}) if ok else r.fail("; ".join(details))


def preflight_p2():
    r = Result("P2: Cowork schema-aware Business Skill")
    t0 = time.time()
    if not BUSINESS_SKILLS.exists():
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(f"missing {_rel(BUSINESS_SKILLS)}")

    candidates = []
    for path in BUSINESS_SKILLS.glob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        lower = text.lower()
        has_cowork = re.search(r"\bcowork\b", text, re.IGNORECASE) is not None
        has_mcp = re.search(r"\bmcp\b", text, re.IGNORECASE) is not None
        table_hits = [
            term
            for term in ["lc_launch", "lc_milestone", "lc_task", "lc_teammember", "lc_statusupdate"]
            if term in text
        ]
        rule_hits = [
            term
            for term in ["lookup", "relationship", "lc_isblocked", "lc_taskstatus"]
            if term.lower() in lower
        ]
        if has_cowork and has_mcp and len(table_hits) >= 3 and len(rule_hits) >= 2:
            score = len(table_hits) + len(rule_hits) + 5
            candidates.append((score, path, table_hits, rule_hits))

    r.elapsed_ms = int((time.time() - t0) * 1000)
    if not candidates:
        return r.fail(
            "No Cowork + Dataverse MCP schema skill found in business-skills/. "
            "Create the Step 6 Business Skill before recording."
        )
    candidates.sort(reverse=True, key=lambda item: item[0])
    score, path, table_hits, rule_hits = candidates[0]
    return r.ok(
        f"{_rel(path)} score={score}",
        {"path": _rel(path), "score": score, "tables": table_hits, "rules": rule_hits},
    )


def preflight_p3():
    r = Result("P3: Cowork plugin package files")
    t0 = time.time()
    found_dirs = [d for d in PLUGIN_CANDIDATE_DIRS if d.exists()]
    if not found_dirs:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        expected = [_rel(d) for d in PLUGIN_CANDIDATE_DIRS]
        return r.fail("No Cowork plugin package directory found", {"expected_any_of": expected})

    details = []
    payload = []
    ok = True
    for base in found_dirs:
        jsons = _json_files(base)
        manifests = [p for p in jsons if p.name.lower() == "manifest.json"]
        actionish = [p for p in jsons if any(x in p.name.lower() for x in ["action", "plugin", "mcp", "api"])]
        if not manifests:
            ok = False
            details.append(f"{_rel(base)} missing manifest.json")
        if not actionish:
            ok = False
            details.append(f"{_rel(base)} missing action/plugin json")
        payload.append({
            "dir": _rel(base),
            "manifest": [_rel(p) for p in manifests],
            "actionish": [_rel(p) for p in actionish],
        })
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if ok:
        return r.ok(f"{len(found_dirs)} package dir(s) found", payload)
    return r.fail("; ".join(details), payload)


def preflight_p4():
    r = Result("P4: Plugin action points to Dataverse MCP")
    t0 = time.time()
    found_dirs = [d for d in PLUGIN_CANDIDATE_DIRS if d.exists()]
    if not found_dirs:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail("No plugin package directory to inspect")

    hits = []
    for base in found_dirs:
        for path in _text_files(base):
            text = path.read_text(encoding="utf-8", errors="replace")
            lower = text.lower()
            hit = {
                "path": _rel(path),
                "api_mcp": "/api/mcp" in lower,
                "oauth_vault": "oauthpluginvault" in lower,
                "reference_id": "referenceid" in lower or "reference_id" in lower,
            }
            if any(hit.values()):
                hits.append(hit)

    aggregate = {
        "api_mcp": any(h["api_mcp"] for h in hits),
        "oauth_vault": any(h["oauth_vault"] for h in hits),
        "reference_id": any(h["reference_id"] for h in hits),
    }
    r.elapsed_ms = int((time.time() - t0) * 1000)
    missing = [key for key, value in aggregate.items() if not value]
    if missing:
        return r.fail(f"missing markers: {missing}", {"hits": hits, "aggregate": aggregate})
    return r.ok("/api/mcp + OAuthPluginVault + referenceId found", {"hits": hits})


def test_1_whoami():
    r = Result("T1: Dataverse WhoAmI via scripts/auth.py")
    status, payload, elapsed_ms = _req("GET", "WhoAmI()")
    r.elapsed_ms = elapsed_ms
    if status != 200:
        return r.fail(f"HTTP {status}: {payload}", payload)
    return r.ok(f"UserId={payload.get('UserId')}", payload)


def test_2_core_tables():
    r = Result("T2: Core Launch Control tables exist")
    t0 = time.time()
    missing = []
    present = []
    for table in CORE_TABLES:
        path = "EntityDefinitions(LogicalName='{}')?$select=LogicalName,SchemaName,DisplayName".format(table)
        status, payload, _ = _req("GET", path)
        if status == 200:
            present.append(table)
        else:
            missing.append({"table": table, "status": status, "payload": payload})
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if missing:
        return r.fail(f"missing/blocked tables: {[m['table'] for m in missing]}", {"present": present, "missing": missing})
    return r.ok(f"{len(present)} tables present: {', '.join(present)}", {"present": present})


def run_all():
    results = []
    p1 = preflight_p1()
    results.append(p1)
    results.append(preflight_p2())
    results.append(preflight_p3())
    results.append(preflight_p4())

    if p1.passed:
        for fn in [test_1_whoami, test_2_core_tables]:
            try:
                results.append(fn())
            except Exception as ex:
                r = Result(fn.__name__.replace("_", " "))
                results.append(r.fail(f"{ex.__class__.__name__}: {ex}"))
    else:
        for name in [
            "T1: Dataverse WhoAmI via scripts/auth.py",
            "T2: Core Launch Control tables exist",
        ]:
            results.append(Result(name).fail("Skipped because P1 failed"))
    return results


def render_console(results):
    print()
    print(C.BOLD + "Episode 6 - Cowork Plugin Preflight" + C.END)
    print("=" * 72)
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    for r in results:
        if r.passed is None:
            tag = C.YELLOW + "SKIP" + C.END
        elif r.passed:
            tag = C.GREEN + " OK " + C.END
        else:
            tag = C.RED + "FAIL" + C.END
        print(f"  [{tag}] {r.name}  {C.DIM}({r.elapsed_ms}ms){C.END}")
        if r.detail:
            print(f"         {C.DIM}{r.detail}{C.END}")
    print("=" * 72)
    color = C.GREEN if passed == total else (C.YELLOW if passed > 0 else C.RED)
    print(f"  {color}{passed}/{total} passing{C.END}")
    print()


def render_markdown(results):
    lines = [
        "# Episode 6 - Cowork Plugin Preflight Results",
        "",
        f"**Environment:** `{_dataverse_url() or 'not set'}`",
        "",
        "| Test | Result | Time | Detail |",
        "|------|--------|------|--------|",
    ]
    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        detail = (r.detail or "").replace("|", "\\|")
        lines.append(f"| {r.name} | {icon} | {r.elapsed_ms}ms | {detail} |")
    lines.append("")
    lines.append("## Payloads")
    for r in results:
        if r.payload is not None:
            lines.append("")
            lines.append(f"### {r.name}")
            lines.append("```json")
            lines.append(json.dumps(r.payload, indent=2, default=str)[:4000])
            lines.append("```")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true", help="Emit the test plan (markdown) for review")
    p.add_argument("--run", action="store_true", help="Execute read-only preflight checks")
    p.add_argument("--out", default=None, help="Optional path to write results markdown")
    args = p.parse_args()

    if not (args.plan or args.run):
        p.print_help()
        sys.exit(2)
    if args.plan:
        print(PLAN)
    if args.run:
        results = run_all()
        render_console(results)
        if args.out:
            Path(args.out).write_text(render_markdown(results), encoding="utf-8")
            print(f"  Results written: {args.out}")
        sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
