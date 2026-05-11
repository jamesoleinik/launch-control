"""Local test harness for Episode 6 — The Agent.

Two modes:
  python scripts/test_ep6_locally.py --plan       # Emit human-readable test plan (markdown)
  python scripts/test_ep6_locally.py --run        # Execute tests, print colorized summary, write results md
  python scripts/test_ep6_locally.py --plan --run # Both: show plan, then run

The Copilot Studio agent itself can't be programmatically invoked (no public
eval endpoint yet). What we *can* do is verify the substrate the agent
depends on, then provide a manual prompt set for the CS Test panel.

Pre-flight (substrate):
  P1: lc_knowledgearticle table is in LaunchControl solution
  P2: At least 4 lc_knowledgearticle records exist
  P3: Every record has lc_summary and lc_document populated
  P4: All four KB categories represented (Policy, Playbook, Spec, Postmortem)
  P5: lc_CalculateLaunchReadiness Custom API exists (re-checks Ep 5)
  P6: system-prompt.txt and declarativeAgent.json instructions are in sync

Smoke tests:
  T1: Knowledge records are queryable via OData (sanity for KB index)
  T2: lc_CalculateLaunchReadiness invokes successfully (the agent's tool)
  T3: lc_githubissue virtual entity returns rows (cross-system state)

Manual prompts:
  Writes scripts/test_ep6_prompts.md with the prompt scenarios from the
  system prompt's Knowledge Grounding routing table — Knowledge-only,
  MCP-only, and Both — for you to run in the CS Test panel.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.auth import get_token, load_env  # noqa: E402

load_env()
ENV = os.environ["DATAVERSE_URL"].rstrip("/")
TOK = None

REPO_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT_PATH = REPO_ROOT / "agents" / "launch-coordinator" / "system-prompt.txt"
DECLARATIVE_AGENT_PATH = REPO_ROOT / "agents" / "launch-coordinator" / "declarativeAgent.json"


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


# ---------- Test plan ----------

PLAN = """# Episode 6 — Local Test Plan

> Review this plan before running. Goal: prove the substrate the Launch
> Coordinator agent depends on (Dataverse Knowledge, Custom API, virtual
> entity, sync'd system prompt) is correctly wired, **then** validate the
> agent itself manually in the Copilot Studio Test panel.

## Why we can't auto-run the agent

Copilot Studio doesn't expose a public eval/invoke endpoint that's stable
for agents. The harness verifies what we *can* verify programmatically (the
substrate) and emits a manual prompt set for the CS Test panel.

## Pre-flight — substrate checks (read-only)

| # | Check | What it proves |
|---|-------|----------------|
| P1 | `lc_knowledgearticle` is in `LaunchControl` solution | Knowledge source is exportable / open-sourceable |
| P2 | >=4 `lc_knowledgearticle` records exist | All sample KB docs uploaded |
| P3 | Every record has non-empty `lc_summary` AND populated `lc_document` | File column upload succeeded |
| P4 | All 4 KB categories represented (Policy, Playbook, Spec, Postmortem) | Routing scenarios covered |
| P5 | `lc_CalculateLaunchReadiness` Custom API exists | Agent's go/no-go tool is callable |
| P6 | `system-prompt.txt` matches `declarativeAgent.json` instructions | Sync rule honored |

## Smoke tests

| # | Test | What it proves |
|---|------|----------------|
| T1 | OData query: KB records are searchable text | `lc_summary` is fts-eligible |
| T2 | Smoke: invoke `lc_CalculateLaunchReadiness('Q3 Widget Launch')` | Custom API tool live |
| T3 | OData query: `lc_githubissue` virtual entity returns rows | Cross-system state still works |

## Manual prompt set

After the harness passes, run these in Copilot Studio's Test panel
(`scripts/test_ep6_prompts.md` is regenerated each run):

- **Knowledge-only** prompts (should cite article title, no MCP call):
  - "What's our policy on slipping a launch by a week?"
  - "How do we run a launch readiness review?"
  - "What did we learn from the Q1 Widget Mini launch?"
  - "Summarize the Q3 Widget Pro launch brief."
- **MCP-only** prompts (should query Dataverse, no Knowledge call):
  - "What's the status of Q3 Widget Launch?"
  - "Which tasks are blocked right now?"
  - "Is Q3 Widget Launch ready to ship?"
- **Both** prompts (should chain Knowledge + MCP):
  - "Should we slip Q3 Widget Launch by a week? What does our policy say and what's the live status?"
  - "Are we repeating Q1 Widget Mini's mistakes on Q3?"

## Outputs

- `--run` writes `test_results_ep6_<timestamp>.md` next to this script
- Console prints a green/red summary with timings
- Manual prompt set written to `scripts/test_ep6_prompts.md`
- Exit code 0 on full pass, 1 on any failure

## Out-of-scope

- Programmatic invocation of the CS agent itself (no stable endpoint)
- Verifying the tenant-level "search multiline + file" preview flag (manual)
- Verifying the agent has been published in CS (manual via the Test panel)
"""


# ---------- Result + tests ----------

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

    def fail(self, detail, payload=None):
        self.passed = False
        self.detail = detail
        self.payload = payload
        return self


def _solution_id(name):
    body = get(f"solutions?$filter=uniquename eq '{name}'&$select=solutionid")
    rows = body.get("value", [])
    return rows[0]["solutionid"] if rows else None


def preflight_p1():
    r = Result("P1: lc_knowledgearticle in LaunchControl solution")
    t0 = time.time()
    sid = _solution_id("LaunchControl")
    if not sid:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail("LaunchControl solution not found")
    meta = get(
        "EntityDefinitions(LogicalName='lc_knowledgearticle')?$select=MetadataId,LogicalName"
    )
    metaid = meta.get("MetadataId")
    if not metaid:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail("lc_knowledgearticle table not found")
    comps = get(
        f"solutioncomponents?$filter=_solutionid_value eq {sid} and objectid eq {metaid}"
        "&$select=componenttype,objectid"
    )["value"]
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if any(c["componenttype"] == 1 for c in comps):
        return r.ok(f"componenttype=1 (Entity), solution={sid}", payload={"metaid": metaid})
    return r.fail(f"lc_knowledgearticle (metaid={metaid}) not in LaunchControl solution")


def preflight_p2():
    r = Result("P2: >=4 lc_knowledgearticle records")
    t0 = time.time()
    body = get(
        "lc_knowledgearticles?$select=lc_knowledgearticleid,lc_title,lc_category,lc_summary"
        "&$top=20"
    )
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    r.payload = rows
    if len(rows) >= 4:
        names = ", ".join((row.get("lc_title") or "(untitled)") for row in rows[:4])
        return r.ok(f"found {len(rows)}: {names}", payload=rows)
    return r.fail(f"Only {len(rows)} record(s) found", payload=rows)


def preflight_p3(records):
    r = Result("P3: All records have summary + document populated")
    if not records:
        return r.fail("No records to check")
    t0 = time.time()
    missing_summary = []
    missing_doc = []
    for rec in records:
        rid = rec["lc_knowledgearticleid"]
        title = rec.get("lc_title") or "(untitled)"
        if not (rec.get("lc_summary") or "").strip():
            missing_summary.append(title)
            continue
        # Probe the file column with a HEAD-style $value GET
        path = f"lc_knowledgearticles({rid})/lc_document/$value"
        url = ENV + "/api/data/v9.2/" + path
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", "Bearer " + _tok())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.length is not None and resp.length == 0:
                    missing_doc.append(title)
                # read tiny chunk to confirm bytes flow
                chunk = resp.read(64)
                if not chunk:
                    missing_doc.append(title)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                missing_doc.append(title)
            else:
                missing_doc.append(f"{title} (HTTP {e.code})")
        except Exception as ex:
            missing_doc.append(f"{title} ({ex.__class__.__name__})")
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if missing_summary or missing_doc:
        return r.fail(
            f"missing summary: {missing_summary or 'none'}; missing doc: {missing_doc or 'none'}",
            payload={"missing_summary": missing_summary, "missing_doc": missing_doc},
        )
    return r.ok(f"all {len(records)} records complete")


CATEGORY_VALUES = {
    "Policy": 10600100,
    "Playbook": 10600101,
    "Spec": 10600102,
    "Postmortem": 10600103,
}


def preflight_p4(records):
    r = Result("P4: All 4 KB categories represented")
    if not records:
        return r.fail("No records to check")
    seen = {rec.get("lc_category") for rec in records}
    expected = set(CATEGORY_VALUES.values())
    missing = expected - seen
    if missing:
        rev = {v: k for k, v in CATEGORY_VALUES.items()}
        miss_names = [rev[v] for v in missing]
        return r.fail(f"missing categories: {miss_names}", payload={"seen": list(seen)})
    return r.ok("Policy, Playbook, Spec, Postmortem all present")


def preflight_p5():
    r = Result("P5: CustomAPI lc_CalculateLaunchReadiness exists")
    t0 = time.time()
    body = get(
        "customapis?$filter=uniquename eq 'lc_CalculateLaunchReadiness'"
        "&$select=customapiid,uniquename,displayname"
    )
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    if rows:
        return r.ok(f"id={rows[0]['customapiid']}", payload=rows[0])
    return r.fail("CustomAPI not found — Episode 5 setup may not have run")


def _normalize(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", text).strip()


def preflight_p6():
    r = Result("P6: system-prompt is in sync across files")
    t0 = time.time()
    if not SYSTEM_PROMPT_PATH.exists():
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(f"missing {SYSTEM_PROMPT_PATH}")
    if not DECLARATIVE_AGENT_PATH.exists():
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(f"missing {DECLARATIVE_AGENT_PATH}")
    src = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    da = json.loads(DECLARATIVE_AGENT_PATH.read_text(encoding="utf-8"))
    declarative_instructions = da.get("instructions") or ""
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if _normalize(src) == _normalize(declarative_instructions):
        return r.ok(f"{len(src)} chars in sync")
    # Show first divergence for triage
    s_norm = _normalize(src)
    d_norm = _normalize(declarative_instructions)
    for i, (a, b) in enumerate(zip(s_norm, d_norm)):
        if a != b:
            window = 40
            return r.fail(
                f"diverge at char {i}: prompt='...{s_norm[max(0,i-window):i+window]}...' vs "
                f"declarative='...{d_norm[max(0,i-window):i+window]}...'",
                payload={"prompt_len": len(s_norm), "declarative_len": len(d_norm)},
            )
    return r.fail(
        f"length mismatch: prompt={len(s_norm)}, declarative={len(d_norm)}",
        payload={"prompt_len": len(s_norm), "declarative_len": len(d_norm)},
    )


def test_1_kb_searchable(records):
    r = Result("T1: Knowledge OData query returned text")
    t0 = time.time()
    if not records:
        return r.fail("No records to query")
    # Confirm the KB rows have non-trivial summary length (proxy for searchable content)
    word_counts = []
    for rec in records:
        summary = rec.get("lc_summary") or ""
        word_counts.append(len(summary.split()))
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if min(word_counts) < 5:
        return r.fail(f"some summary too short: min words={min(word_counts)}")
    return r.ok(f"all {len(records)} summaries >=5 words; min={min(word_counts)}, max={max(word_counts)}")


def test_2_custom_api():
    r = Result("T2: Smoke test — invoke lc_CalculateLaunchReadiness")
    body = {"lc_LaunchName": "Q3 Widget Launch"}
    status, resp, ms = _req("POST", "lc_CalculateLaunchReadiness", body=body)
    r.elapsed_ms = ms
    if status != 200:
        return r.fail(f"HTTP {status}: {resp}", payload={"request": body, "response": resp})
    score = resp.get("lc_ReadinessScore")
    verdict = resp.get("lc_Verdict")
    payload = {"request": body, "response": resp}
    if score is None or verdict is None:
        return r.fail("Missing score or verdict in response", payload=payload)
    return r.ok(f"Score={score}, Verdict={verdict}", payload=payload)


def test_3_github_ve():
    r = Result("T3: lc_githubissue virtual entity returns rows")
    t0 = time.time()
    try:
        body = get("lc_githubissues?$top=5&$select=lc_issuenumber,lc_state,lc_name")
    except RuntimeError as e:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(str(e))
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    if not rows:
        return r.fail("VE returned 0 rows — GitHub provider may be down or repo is empty")
    return r.ok(f"{len(rows)} issue(s) returned", payload=rows[:3])


# ---------- Reporting ----------

def render_console(results):
    print()
    print(C.BOLD + "Episode 6 — Local Test Run" + C.END)
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
    lines = [
        "# Episode 6 — Local Test Results",
        f"_Generated: {ts}_",
        "",
        f"**Environment:** `{ENV}`",
        "",
    ]
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    icon = "✅" if passed == total else ("⚠️" if passed > 0 else "❌")
    lines.append(f"## Summary: {icon} {passed}/{total} passing")
    lines.append("")
    lines.append("| Test | Result | Time | Detail |")
    lines.append("|------|--------|------|--------|")
    for r in results:
        ic = "✅" if r.passed else "❌"
        detail = (r.detail or "").replace("|", "\\|")
        lines.append(f"| {r.name} | {ic} | {r.elapsed_ms}ms | {detail} |")
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


PROMPT_DOC = """# Episode 6 — Manual Prompt Set (Copilot Studio Test panel)

_Generated by `scripts/test_ep6_locally.py`. Re-run after substrate changes._

The local harness verifies the substrate (Knowledge records, Custom API,
sync'd system prompt). This file is the human-driven validation against the
agent itself — paste each prompt into the Test panel and check the trace.

## Knowledge-only (should call Dataverse Knowledge, cite article title)

1. **"What's our policy on slipping a launch by a week?"**
   - Expected tool: `Dataverse Knowledge`
   - Expected citation: _Escalation Policy_
2. **"Walk me through the launch readiness checklist."**
   - Expected tool: `Dataverse Knowledge`
   - Expected citation: _Launch Readiness Playbook_
3. **"What went wrong with the Q1 Widget Mini launch?"**
   - Expected tool: `Dataverse Knowledge`
   - Expected citation: _Postmortem - Q1 Widget Mini Launch_
4. **"Summarize the Q3 Widget Pro launch brief."**
   - Expected tool: `Dataverse Knowledge`
   - Expected citation: _Q3 Widget Pro - Product Launch Brief_

## MCP-only (should call Dataverse MCP, no Knowledge)

5. **"What's the status of Q3 Widget Launch?"**
   - Expected tool: Dataverse MCP `lc_launch` query
6. **"Which tasks are blocked right now?"**
   - Expected tool: Dataverse MCP `lc_task` query (`lc_isblocked eq true`)
7. **"Is Q3 Widget Launch ready to ship?"**
   - Expected tool: Custom API `lc_CalculateLaunchReadiness`
   - Expected response shape: `Score` + `Verdict` + `Summary` (no hand-rolled scoring)
8. **"Show me overdue milestones for Q3 Widget Launch."**
   - Expected tool: Dataverse MCP `lc_milestone` query

## Both — Knowledge + MCP (the money shot)

9. **"Should we slip Q3 Widget Launch by a week? What does our policy say and what's the live status?"**
   - Expected tools: `Dataverse Knowledge` (Escalation Policy) + Custom API + Dataverse MCP
   - Expected response: cite the policy AND report current Verdict
10. **"Are we on track for Q3 Widget Pro launch readiness based on our playbook?"**
    - Expected tools: `Dataverse Knowledge` (Playbook) + Custom API
11. **"Based on the Q1 postmortem, are we repeating any of those mistakes on Q3?"**
    - Expected tools: `Dataverse Knowledge` (Postmortem) + Dataverse MCP `lc_task` query

## Negative tests (should refuse / clarify, not hallucinate)

12. **"What's the budget for Q3 Widget Launch?"**
    - Expected: agent admits there's no budget field; doesn't invent
13. **"Who's the CEO?"**
    - Expected: politely declines (out of scope)
14. **"Mark the Security Review milestone as Complete."**
    - Expected: agent first checks the GitHub VE state for any linked
      tasks, then asks for confirmation before patching `lc_milestonestatus`

## What to verify in the trace panel

- **Tool name** — `Dataverse Knowledge` for 1–4, MCP record tools for 5–8,
  both for 9–11.
- **Citation in the response body** for Knowledge calls.
- **For Custom API** — only `lc_CalculateLaunchReadiness` is invoked; the
  agent doesn't re-tally gates client-side.
- **For Status Transition Rules** — agent refuses Done on engineering tasks
  whose linked GitHub issue is still `open`.

## When something fails

| Symptom | Most likely cause |
|---------|-------------------|
| Agent gives policy answer but no citation | Knowledge tool not attached, or system prompt's "cite the article title" line missing |
| Agent re-tallies gates by hand | Custom API not exposed (re-attach Dataverse MCP) or system prompt lost the "always invoke" line |
| Knowledge call returns nothing | Tenant-level "Search support for multiline text and file data types" preview flag not enabled (PPAC → env → Settings → Product → Features) |
| Agent doesn't know about `lc_knowledgearticle` | System prompt not pasted/published in CS after the latest edit; declarative agent's `instructions` not synced |
"""


def write_prompt_set():
    out = Path(__file__).resolve().parent / "test_ep6_prompts.md"
    out.write_text(PROMPT_DOC, encoding="utf-8")
    return out


def run_all():
    results = []
    p1 = preflight_p1()
    results.append(p1)
    p2 = preflight_p2()
    results.append(p2)
    records = p2.payload if p2.passed else []
    results.append(preflight_p3(records))
    results.append(preflight_p4(records))
    results.append(preflight_p5())
    results.append(preflight_p6())
    results.append(test_1_kb_searchable(records))
    results.append(test_2_custom_api())
    results.append(test_3_github_ve())
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true", help="Emit the test plan (markdown) for review")
    p.add_argument("--run", action="store_true", help="Execute tests")
    p.add_argument("--out", default=None, help="Path to write results markdown")
    args = p.parse_args()
    if not (args.plan or args.run):
        p.print_help()
        sys.exit(2)
    if args.plan:
        print(PLAN)
    if args.run:
        results = run_all()
        render_console(results)
        out_path = args.out or str(
            Path(__file__).resolve().parent
            / f"test_results_ep6_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        Path(out_path).write_text(render_markdown(results), encoding="utf-8")
        prompt_path = write_prompt_set()
        print(f"  Results written:    {out_path}")
        print(f"  Manual prompt set:  {prompt_path}")
        sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
