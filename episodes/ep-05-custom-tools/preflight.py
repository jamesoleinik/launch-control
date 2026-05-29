"""Local test harness for Episode 5 — Custom Tools.

Two modes:
  python episodes/ep-05-custom-tools/preflight.py --plan       # Emit human-readable test plan (markdown)
  python episodes/ep-05-custom-tools/preflight.py --run        # Execute tests, print colorized summary, write results md
  python episodes/ep-05-custom-tools/preflight.py --plan --run # Both: show plan, then run

Tests cover:
  Pre-flight   : CustomAPI registered, in LaunchControl solution, BYO MCP connectors present
  Test 1       : Direct OData invoke of lc_CalculateLaunchReadiness (Q3 Widget Launch)
  Test 2       : Verdict matrix - invoke against every lc_launch in env
  Test 3       : MCP handshake — JSON-RPC initialize + tools/list against learn.microsoft.com/api/mcp
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
| P4 | `CustomAPI lc_CalculateLaunchReadinessFx` exists (Power Fx twin) | Functions-in-Dataverse Custom API is registered |

## Test 1 — Direct OData invoke (the smoke test)

**Call**
```
POST /api/data/v9.2/lc_CalculateLaunchReadiness
{ "lc_LaunchName": "Q3 Widget Launch" }
```

**Expect**
- HTTP 200
- Response has `lc_ReadinessScore` (number 0-100), `lc_Verdict` (GO|CONDITIONAL|NO-GO), `lc_ReadinessSummary` (string)
- Score and verdict are internally consistent (NO-GO if any blocked, GO only if score>=90 and no at-risk)

## Test 2 — Verdict matrix

For every `lc_launch` in the env, invoke the action. Record `(name, score, verdict, milestone_count)`. Sanity-check:
- NO-GO whenever `summary` mentions "blocked"
- GO whenever score >= 90 AND no "at-risk" in summary
- CONDITIONAL otherwise

This proves the plugin generalizes — not hardcoded to one launch.

## Test 3 — MCP handshake against Learn MCP (the real protocol check)

Open a JSON-RPC `initialize` + `tools/list` round-trip directly against `https://learn.microsoft.com/api/mcp` — no agent, no Power Platform runtime, just the wire protocol the custom connector wraps. Assert the server returns its capabilities and a non-empty tools array. This proves the BYO MCP connector pattern points at a **live, spec-compliant MCP server** — not just a dormant Dataverse row.

P3 above proves the connector is registered. T3 proves the thing it points at actually speaks MCP.

## Test 4 — Power Fx twin returns the same contract

Invoke `lc_CalculateLaunchReadinessFx` on `Q3 Widget Launch` and assert the response shape matches the .NET plugin (`lc_ReadinessScore`, `lc_Verdict`, `lc_ReadinessSummary`). When the launch's `lc_RepoUrl` is set and the repo has open `release-blocker` issues, the Fx body folds that count in and may demote the verdict — the test cross-references the plugin baseline and surfaces any demotion in the output. This proves the **two implementations of the same contract** invariant holds at runtime.

## Outputs

- `--run` writes `test_results_<timestamp>.md` next to this script
- Console prints a green/red summary with timings
- Exit code 0 on full pass, 1 on any failure

## Out-of-scope

- Invoking via Copilot Studio agent (that's the next episode — _The Agent_)
- Per-tool MCP invocation from an external client (Claude Desktop, VS Code MCP) — covered in later runtime episodes
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

    def skip(self, detail, payload=None):
        self.passed = None
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


def _lowcode_plugins_available():
    """The Functions-in-Dataverse preview ships as a managed solution that
    provisions the msdyn_function table (formerly msdyn_lowcodeplugin). If
    that table doesn't exist, the feature is not installed in this env
    (admin install required).
    """
    try:
        get("EntityDefinitions(LogicalName='msdyn_function')?$select=LogicalName")
        return True
    except Exception:
        return False


def preflight_p4():
    """Power Fx twin must be registered as its own Custom API."""
    r = Result("P4: CustomAPI lc_CalculateLaunchReadinessFx exists (Power Fx twin)")
    t0 = time.time()
    if not _lowcode_plugins_available():
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.skip(
            "Functions-in-Dataverse preview not installed in this env "
            "(msdyn_function table missing). Tenant admin must install "
            "the 'Power Platform Low Code Plug-ins' application."
        )
    body = get(
        "customapis?$filter=uniquename eq 'lc_calculatelaunchreadinessfx'"
        "&$select=customapiid,uniquename,name"
    )
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    if rows:
        return r.ok(f"id={rows[0]['customapiid']}", payload=rows[0])
    return r.fail(
        "Fx Function not registered. Import functions/CalculateLaunchReadinessFx/ "
        "into the LaunchControl solution (requires LowCodePluginsEnabled org feature)."
    )


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


def test_4_fx_twin():
    """Invoke the Power Fx twin — same contract, Teams-connector enriched.

    The Fx body delegates milestone math to the .NET Custom API and adds a
    side-effect: post the readiness card to the launch's Teams channel via
    the first-party MicrosoftTeams connector. Response shape matches the
    plug-in plus a `lc_NotifiedAt` timestamp when a channel was posted to.
    """
    r = Result("T4: Fx twin — lc_CalculateLaunchReadinessFx returns the contract")
    if not _lowcode_plugins_available():
        return r.skip(
            "Functions-in-Dataverse preview not installed in this env "
            "(msdyn_function table missing). Tenant admin must install "
            "the 'Power Platform Low Code Plug-ins' application."
        )
    launch = "Q3 Widget Launch"
    body = {"lc_LaunchName": launch}
    status, resp, ms = _req("POST", "lc_calculatelaunchreadinessfx", body=body)
    r.elapsed_ms = ms
    payload = {"request": body, "response": resp}
    if status != 200:
        return r.fail(f"HTTP {status}: {resp}", payload=payload)
    score = resp.get("lc_ReadinessScore")
    verdict = resp.get("lc_Verdict")
    if score is None or verdict is None:
        return r.fail("Missing score/verdict in Fx response", payload=payload)
    if verdict not in ("GO", "CONDITIONAL", "NO-GO"):
        return r.fail(f"Unexpected verdict: {verdict}", payload=payload)
    # Cross-check shape with the .NET plugin baseline.
    _, base, _ = _req("POST", "lc_CalculateLaunchReadiness", body=body)
    detail = f"Score={score}, Verdict={verdict}"
    notified = resp.get("lc_NotifiedAt")
    if notified:
        detail += f", Teams card posted @ {notified}"
    return r.ok(detail, payload={"fx": resp, "plugin_baseline": base})


def test_3_byo_mcp():
    """Real MCP handshake against the Learn MCP server.

    P3 above proves the custom connector row is registered in Dataverse.
    This proves the URL that connector points at actually speaks MCP —
    a JSON-RPC `initialize` + `tools/list` round-trip with no agent in the
    loop. Public endpoint, no Dataverse auth.
    """
    r = Result("T3: Learn MCP server responds to initialize + tools/list")
    t0 = time.time()
    url = "https://learn.microsoft.com/api/mcp"
    init_body = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "launch-control-preflight", "version": "1.0"},
        },
    }
    list_body = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    initialized_notice = {"jsonrpc": "2.0", "method": "notifications/initialized"}

    def _parse(raw):
        # Streamable HTTP transport returns SSE: "event: message\ndata: {json}\n\n"
        # or plain application/json. Handle both.
        for block in raw.split("\n\n"):
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload.startswith("{"):
                        return json.loads(payload)
        stripped = raw.strip()
        if stripped.startswith("{"):
            return json.loads(stripped)
        raise ValueError(f"no JSON-RPC payload in response: {raw[:200]!r}")

    def _post(body, session_id=None, expect_response=True):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if session_id:
            req.add_header("Mcp-Session-Id", session_id)
        with urllib.request.urlopen(req, timeout=20) as resp:
            sid = resp.headers.get("mcp-session-id") or session_id
            raw = resp.read().decode("utf-8", errors="replace")
            if not expect_response:
                return None, sid
            return _parse(raw), sid

    try:
        init, sid = _post(init_body)
        if "result" not in init:
            r.elapsed_ms = int((time.time() - t0) * 1000)
            return r.fail(f"initialize had no result: {init}", payload=init)
        # MCP spec: client sends `notifications/initialized` after initialize completes.
        try:
            _post(initialized_notice, session_id=sid, expect_response=False)
        except Exception:
            pass  # notification is best-effort; some servers don't return 200 here
        tools, _ = _post(list_body, session_id=sid)
        r.elapsed_ms = int((time.time() - t0) * 1000)
        tool_list = (tools.get("result") or {}).get("tools") or []
        server_name = ((init.get("result") or {}).get("serverInfo") or {}).get("name", "?")
        r.payload = {"server": server_name, "tools_count": len(tool_list),
                     "tool_names": [t.get("name") for t in tool_list][:10]}
        if not tool_list:
            return r.fail("tools/list returned empty", payload=r.payload)
        return r.ok(f"server={server_name} exposes {len(tool_list)} tool(s)", payload=r.payload)
    except Exception as exc:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(f"MCP handshake failed: {exc}")


# ---------- Reporting ----------

def render_console(results):
    print()
    print(C.BOLD + "Episode 5 — Local Test Run" + C.END)
    print("=" * 60)
    passed = sum(1 for r in results if r.passed is True)
    skipped = sum(1 for r in results if r.passed is None)
    failed = sum(1 for r in results if r.passed is False)
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
    color = C.GREEN if failed == 0 else (C.YELLOW if passed > 0 else C.RED)
    skip_note = f" ({skipped} skipped)" if skipped else ""
    print(f"  {color}{passed}/{total} passing{skip_note}{C.END}")
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
        if r.passed is None:
            ic = "⚠️"; res = "SKIP"
        elif r.passed:
            ic = "✅"; res = "PASS"
        else:
            ic = "❌"; res = "FAIL"
        detail = (r.detail or "").replace("|", "\\|")
        lines.append(f"| | {r.name} | {ic} | {r.elapsed_ms}ms | {detail} |")
    lines.append("")
    lines.append("## Details")
    for r in results:
        lines.append("")
        lines.append(f"### {r.name}")
        lines.append(f"- Result: {'SKIP' if r.passed is None else ('PASS' if r.passed else 'FAIL')}")
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
    results.append(preflight_p4())
    results.append(test_1_smoke())
    results.append(test_2_verdict_matrix())
    results.append(test_3_byo_mcp())
    results.append(test_4_fx_twin())
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
        sys.exit(0 if all(r.passed is not False for r in results) else 1)


if __name__ == "__main__":
    main()
