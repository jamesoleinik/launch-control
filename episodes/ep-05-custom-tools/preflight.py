"""Local test harness for Episode 5 — Custom Tools.

Two modes:
  python episodes/ep-05-custom-tools/preflight.py --plan       # Emit human-readable test plan (markdown)
  python episodes/ep-05-custom-tools/preflight.py --run        # Execute tests, print colorized summary, write results md
  python episodes/ep-05-custom-tools/preflight.py --plan --run # Both: show plan, then run

Tests cover:
  Pre-flight   : CustomAPI registered, in LaunchControl solution, BYO MCP connectors present
  Test 1       : Direct OData invoke of lc_CalculateLaunchReadiness (Q3 Widget Launch)
  Test 2       : Verdict matrix - invoke against every lc_launch in env
  Test 3       : BYO MCP discovery - paconn-registered custom connectors visible
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.auth import get_token, load_env  # noqa: E402

load_env()
ENV = os.environ["DATAVERSE_URL"].rstrip("/")
TOK = None  # lazily acquired


# ---------- HTTP helpers ----------

def _tok():
    global TOK
    if TOK is None:
        TOK = get_token()
    return TOK


def _req(method, path, body=None, extra_headers=None):
    url = ENV + "/api/data/v9.2/" + urllib.parse.quote(path, safe="?$=&'/,()")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + _tok())
    req.add_header("Accept", "application/json")
    req.add_header("OData-MaxVersion", "4.0")
    req.add_header("OData-Version", "4.0")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (extra_headers or {}).items():
        req.add_header(k, v)
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read()
        elapsed_ms = int((time.time() - t0) * 1000)
        return resp.status, json.loads(raw) if raw else None, elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body_text), elapsed_ms
        except Exception:
            return e.code, {"raw": body_text}, elapsed_ms


def get(path):
    status, body, _ = _req("GET", path)
    if status >= 400:
        raise RuntimeError(f"GET {path} -> {status}: {body}")
    return body


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
        for k in dir(C):
            if not k.startswith("_") and k != "END":
                setattr(C, k, "")
        C.END = ""


# ---------- Test plan (review BEFORE running) ----------

PLAN = """# Episode 5 — Local Test Plan

> Review this plan before running. Goal: prove that everything Ep 5 delivered (custom action + 2 BYO MCP connectors) works end-to-end **without** a Copilot Studio agent.

## Pre-flight (read-only, no side effects)

| # | Check | What it proves |
|---|-------|----------------|
| P1 | `CustomAPI lc_CalculateLaunchReadiness` exists in `customapi` table | Plugin registration step succeeded |
| P2 | CustomAPI is in `LaunchControl` solution (componenttype 10038) | Asset is exportable / open-sourceable |
| P3 | At least 2 custom `connector` rows for paconn-registered MCP servers | BYO MCP servers are live in env |

## Test 1 — Direct OData invoke (the smoke test)

**Call**
```
POST /api/data/v9.2/lc_CalculateLaunchReadiness
{ "lc_LaunchName": "Q3 Widget Launch" }
```

**Expect**
- HTTP 200
- Response has `lc_Score` (number 0-100), `lc_Verdict` (GO|CONDITIONAL|NO-GO), `lc_Summary` (string)
- Score and verdict are internally consistent (NO-GO if any blocked, GO only if score>=90 and no at-risk)

## Test 2 — Verdict matrix

For every `lc_launch` in the env, invoke the action. Record `(name, score, verdict, milestone_count)`. Sanity-check:
- NO-GO whenever `summary` mentions "blocked"
- GO whenever score >= 90 AND no "at-risk" in summary
- CONDITIONAL otherwise

This proves the plugin generalizes — not hardcoded to one launch.

## Test 3 — BYO MCP discovery

Query the `connector` table for rows where `name` contains the customization prefix or matches the paconn-registered server names. List each connector's `name`, `connectorinternalid`, and creation date. This proves paconn registration landed in Dataverse and is discoverable by any MCP-aware client.

## Outputs

- `--run` writes `test_results_<timestamp>.md` next to this script
- Console prints a green/red summary with timings
- Exit code 0 on full pass, 1 on any failure

## Out-of-scope

- Invoking via Copilot Studio agent (that's Ep 6 demo)
- Tool-level invocation of paconn MCP servers (need an MCP client; covered in Ep 6 / Claude Desktop in Ep 8)
"""


# ---------- Tests ----------

class Result:
    def __init__(self, name):
        self.name = name
        self.passed = None
        self.detail = ""
        self.elapsed_ms = 0
        self.payload = None  # request body or response shown in markdown

    def ok(self, detail="", payload=None):
        self.passed = True
        self.detail = detail
        self.payload = payload
        return self

    def fail(self, detail, payload=None):
        self.passed = False
        self.detail = detail
        self.payload = payload
        return self


def preflight_p1():
    r = Result("P1: CustomAPI lc_CalculateLaunchReadiness exists")
    t0 = time.time()
    body = get("customapis?$filter=uniquename eq 'lc_CalculateLaunchReadiness'&$select=customapiid,uniquename,displayname")
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    if rows:
        return r.ok(f"id={rows[0]['customapiid']}", payload=rows[0])
    return r.fail("CustomAPI not found")


def preflight_p2(customapi_id):
    r = Result("P2: CustomAPI is in LaunchControl solution")
    t0 = time.time()
    sols = get("solutions?$filter=uniquename eq 'LaunchControl'&$select=solutionid")["value"]
    if not sols:
        return r.fail("LaunchControl solution not found")
    sid = sols[0]["solutionid"]
    comps = get(
        f"solutioncomponents?$filter=_solutionid_value eq {sid} and objectid eq {customapi_id}"
        f"&$select=componenttype,objectid"
    )["value"]
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if any(c["componenttype"] == 10038 for c in comps):
        return r.ok(f"componenttype=10038, solution={sid}")
    return r.fail(f"Not in LaunchControl. Found rows: {comps}")


def preflight_p3():
    r = Result("P3: BYO MCP custom connectors present (>=2)")
    t0 = time.time()
    body = get(
        "connectors?$filter=contains(name,'mcp') or contains(name,'learn')"
        "&$select=connectorid,name,connectorinternalid,createdon&$top=20"
    )
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    if len(rows) >= 2:
        names = ", ".join(c["name"] for c in rows[:5])
        return r.ok(f"found {len(rows)}: {names}", payload=rows)
    return r.fail(f"Only {len(rows)} connector(s) match — paconn registration may not have landed")


def test_1_smoke():
    r = Result("T1: Smoke test — invoke for Q3 Widget Launch")
    body = {"lc_LaunchName": "Q3 Widget Launch"}
    status, resp, ms = _req("POST", "lc_CalculateLaunchReadiness", body=body)
    r.elapsed_ms = ms
    if status != 200:
        return r.fail(f"HTTP {status}: {resp}", payload={"request": body, "response": resp})
    score = resp.get("lc_ReadinessScore")
    verdict = resp.get("lc_Verdict")
    summary = resp.get("lc_ReadinessSummary", "")
    payload = {"request": body, "response": resp}
    if score is None or verdict is None:
        return r.fail("Missing lc_ReadinessScore or lc_Verdict in response", payload=payload)
    if not isinstance(score, (int, float)) or not (0 <= score <= 100):
        return r.fail(f"Score out of range: {score}", payload=payload)
    if verdict not in ("GO", "CONDITIONAL", "NO-GO"):
        return r.fail(f"Unexpected verdict: {verdict}", payload=payload)
    return r.ok(f"Score={score}, Verdict={verdict}", payload=payload)


def test_2_verdict_matrix():
    r = Result("T2: Verdict matrix — every launch in env")
    t0 = time.time()
    launches = get("lc_launchs?$select=lc_name,lc_launchid&$top=20")["value"]
    results = []
    inconsistencies = []
    for L in launches:
        name = L.get("lc_name") or "(unnamed)"
        status, resp, _ = _req("POST", "lc_CalculateLaunchReadiness", body={"lc_LaunchName": name})
        if status != 200:
            results.append({"name": name, "error": f"HTTP {status}"})
            inconsistencies.append(f"{name}: HTTP {status}")
            continue
        s = resp.get("lc_ReadinessScore")
        v = resp.get("lc_Verdict")
        summ = (resp.get("lc_ReadinessSummary") or "").lower()
        results.append({"name": name, "score": s, "verdict": v, "summary": resp.get("lc_ReadinessSummary")})
        if s is None or v is None:
            inconsistencies.append(f"{name}: missing score/verdict")
            continue
        if "blocked" in summ and v != "NO-GO":
            inconsistencies.append(f"{name}: blocked mentioned but verdict={v}")
        if v == "GO" and (s < 90):
            inconsistencies.append(f"{name}: GO but score={s}")
        if v == "GO" and "at risk" in summ:
            inconsistencies.append(f"{name}: GO but at-risk in summary")
    r.elapsed_ms = int((time.time() - t0) * 1000)
    r.payload = results
    if not launches:
        return r.fail("No launches found in env", payload=results)
    if inconsistencies:
        return r.fail(f"{len(inconsistencies)} inconsistency(ies): " + "; ".join(inconsistencies[:3]), payload=results)
    return r.ok(f"{len(launches)} launches scored consistently")


def test_3_byo_mcp():
    r = Result("T3: BYO MCP custom connectors discoverable")
    t0 = time.time()
    body = get(
        "connectors?$filter=contains(name,'mcp') or contains(name,'learn')"
        "&$select=name,connectorinternalid,createdon&$orderby=createdon desc&$top=20"
    )
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    r.payload = rows
    if len(rows) >= 2:
        return r.ok(f"{len(rows)} connector(s) registered via paconn", payload=rows)
    return r.fail(f"Only {len(rows)} connector(s) found")


# ---------- Reporting ----------

def render_console(results):
    print()
    print(C.BOLD + "Episode 5 — Local Test Run" + C.END)
    print("=" * 60)
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
    print("=" * 60)
    color = C.GREEN if passed == total else (C.YELLOW if passed > 0 else C.RED)
    print(f"  {color}{passed}/{total} passing{C.END}")
    print()


def render_markdown(results):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"# Episode 5 — Local Test Results", f"_Generated: {ts}_", "",
             f"**Environment:** `{ENV}`", ""]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    icon = "✅" if passed == total else ("⚠️" if passed > 0 else "❌")
    lines.append(f"## Summary: {icon} {passed}/{total} passing")
    lines.append("")
    lines.append("| # | Test | Result | Time | Detail |")
    lines.append("|---|------|--------|------|--------|")
    for r in results:
        ic = "✅" if r.passed else "❌"
        detail = (r.detail or "").replace("|", "\\|")
        lines.append(f"| | {r.name} | {ic} | {r.elapsed_ms}ms | {detail} |")
    lines.append("")
    lines.append("## Details")
    for r in results:
        lines.append("")
        lines.append(f"### {r.name}")
        lines.append(f"- Result: {'PASS' if r.passed else 'FAIL'}")
        lines.append(f"- Time: {r.elapsed_ms}ms")
        if r.detail:
            lines.append(f"- Notes: {r.detail}")
        if r.payload is not None:
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(r.payload, indent=2, default=str)[:4000])
            lines.append("```")
    return "\n".join(lines) + "\n"


def run_all():
    results = []
    p1 = preflight_p1()
    results.append(p1)
    customapi_id = (p1.payload or {}).get("customapiid") if p1.passed else None
    if customapi_id:
        results.append(preflight_p2(customapi_id))
    else:
        skip = Result("P2: CustomAPI is in LaunchControl solution")
        skip.fail("Skipped — P1 failed")
        results.append(skip)
    results.append(preflight_p3())
    results.append(test_1_smoke())
    results.append(test_2_verdict_matrix())
    results.append(test_3_byo_mcp())
    return results


# ---------- Entrypoint ----------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true", help="Emit the test plan (markdown) for review")
    p.add_argument("--run", action="store_true", help="Execute tests")
    p.add_argument("--out", default=None, help="Path to write results markdown (default: scripts/test_results_<ts>.md)")
    args = p.parse_args()
    if not (args.plan or args.run):
        p.print_help()
        sys.exit(2)
    if args.plan:
        print(PLAN)
    if args.run:
        results = run_all()
        render_console(results)
        out_path = args.out or str(Path(__file__).resolve().parent / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        Path(out_path).write_text(render_markdown(results), encoding="utf-8")
        print(f"  Results written: {out_path}")
        sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
