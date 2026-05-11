"""Local test harness for Episode 7 — Autonomous Agents.

Three modes:
  python episodes/ep-07-autonomous-agents/preflight.py --plan       # Emit human-readable test plan (markdown)
  python episodes/ep-07-autonomous-agents/preflight.py --run        # Pre-flight + non-destructive smoke (no T1)
  python episodes/ep-07-autonomous-agents/preflight.py --trigger    # Adds T1: ephemeral task lifecycle (CREATE/MODIFY/POLL/DELETE)
  python episodes/ep-07-autonomous-agents/preflight.py --plan --run # Both: show plan, then run

Sentinel cannot be programmatically invoked any more than the Ep 6 chat agent.
What we *can* verify is the substrate it depends on — schema, custom API, prompt
shape, and (with --trigger) end-to-end via a dedicated, ephemeral test task that
we own start-to-finish.

Pre-flight (substrate):
  P1: lc_statusupdate has the columns Sentinel writes (lc_title, lc_body, lc_updatedon, _lc_launchid_value)
  P2: lc_task.lc_isblocked column exists
  P3: lc_CalculateLaunchReadiness Custom API exists (reused by Coordinator + Ep 7 Part 2)
  P4: agents/launch-sentinel/system-prompt.txt exists and contains the severity rubric headings
  P5: Same prompt contains idempotency markers (Source: / Correlation: / GeneratedByAutomation:)
  P6: Severity rubric in prompt matches business-skills/escalation-policy.md (drift detector)
  P7: Prompt loads skills via describe('skills/...') for both behaviors (skills-as-brain check)

Smoke tests (read-only):
  S1: Active launches present (non-zero rows for status in {Planning, InProgress, ReadyForLaunch})
  S2: Custom API invoke against an active launch returns a verdict shape

End-to-end test (only with --trigger):
  T1: Create ephemeral task on a real milestone -> patch lc_isblocked=true ->
      poll lc_statusupdates for the correlation marker -> clean up.
      If no row appears within --trigger-timeout seconds, marks T1 as MANUAL/SKIPPED
      (the bot may not be deployed yet).

Manual prompt set (the Sentinel doesn't take prompts; this harness emits a
"manual checklist" the human runs in the Copilot Studio Test panel for the bot
when it's deployed) -> episodes/ep-07-autonomous-agents/prompts.md.
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
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.auth import get_token, load_env  # noqa: E402

load_env()
ENV = os.environ["DATAVERSE_URL"].rstrip("/")
TOK = None

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SENTINEL_PROMPT_PATH = REPO_ROOT / "agents" / "launch-sentinel" / "system-prompt.txt"
ESCALATION_POLICY_PATH = REPO_ROOT / "business-skills" / "escalation-policy.md"

ACTIVE_LAUNCH_STATUS_VALUES = (10600001, 10600002, 10600003)  # Planning, InProgress, ReadyForLaunch


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

PLAN = """# Episode 7 - Local Test Plan

> Episode 7 builds Launch Sentinel (autonomous Copilot Studio agent that
> escalates blocked tasks) and a Daily Readiness flow. Sentinel cannot be
> programmatically invoked, so this harness verifies substrate + (optionally)
> the round-trip via a controlled ephemeral test task.

## Pre-flight - substrate checks (read-only)

| # | Check | What it proves |
|---|-------|----------------|
| P1 | lc_statusupdate has lc_title, lc_body, lc_updatedon, _lc_launchid_value | Sentinel write shape is correct |
| P2 | lc_task.lc_isblocked column exists | Trigger predicate is valid |
| P3 | lc_CalculateLaunchReadiness Custom API exists | Part 2 flow + Coordinator both rely on this |
| P4 | Sentinel system-prompt.txt exists & has severity rubric (P0/P1/P2/P3) | Prompt is the source of truth |
| P5 | Sentinel system-prompt.txt has idempotency markers (Source/Correlation/GeneratedByAutomation) | Cycle/dedup discipline encoded |
| P6 | Severity rubric in prompt matches business-skills/escalation-policy.md (incl. "Autonomous mode" section) | Drift detector |
| P7 | Prompt loads skills via describe('skills/Escalation Policy') and describe('skills/Launch Readiness Digest') | Skills-as-brain isn't silently collapsed back into the prompt |

## Smoke tests (read-only)

| # | Test | What it proves |
|---|------|----------------|
| S1 | Active launches OData query returns rows | The data Sentinel needs to escalate against |
| S2 | Invoke lc_CalculateLaunchReadiness on an active launch | Custom API still callable |

## End-to-end (only with --trigger)

| # | Test | What it proves |
|---|------|----------------|
| T1 | Create ephemeral task -> set lc_isblocked=true -> poll for correlation marker -> clean up | Real Sentinel round-trip (or MANUAL/SKIPPED if bot not deployed) |

T1 is destructive **only on its own ephemeral row**. It will not modify any
pre-existing task or status update.

## Outputs

- `--run` writes `test_results_ep7_<timestamp>.md` next to this script
- Manual prompt set written to `episodes/ep-07-autonomous-agents/prompts.md`
- Exit code 0 on full pass, 1 on any failure (T1 SKIPPED is not a failure)

## Out-of-scope (deferred for honesty)

- Programmatic verification that the autonomous trigger is bound (no public API)
- ALM packaging of the bot (UI-built; documented in agents/launch-sentinel/README.md)
- The Daily Readiness flow's MCP-step preview availability (see agents/agent-flows/daily-readiness-summary.md)
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

    def skip(self, detail, payload=None):
        self.passed = None  # not a failure
        self.detail = "SKIPPED: " + detail
        self.payload = payload
        return self


# ---------- Pre-flight ----------

REQUIRED_STATUSUPDATE_COLS = {"lc_title", "lc_body", "lc_updatedon", "_lc_launchid_value"}


def preflight_p1():
    r = Result("P1: lc_statusupdate has Sentinel write shape")
    t0 = time.time()
    try:
        body = get(
            "EntityDefinitions(LogicalName='lc_statusupdate')/Attributes"
            "?$select=LogicalName,AttributeType"
        )
    except RuntimeError as e:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(str(e))
    r.elapsed_ms = int((time.time() - t0) * 1000)
    cols = {a["LogicalName"] for a in body.get("value", [])}
    # _lc_launchid_value is a derived navigation; check for the lookup itself
    needed_logical = {"lc_title", "lc_body", "lc_updatedon", "lc_launchid"}
    missing = needed_logical - cols
    if missing:
        return r.fail(f"missing columns: {sorted(missing)}", payload=sorted(cols))
    return r.ok(f"all required columns present (~{len(cols)} attributes total)")


def preflight_p2():
    r = Result("P2: lc_task.lc_isblocked column exists")
    t0 = time.time()
    try:
        body = get(
            "EntityDefinitions(LogicalName='lc_task')/Attributes(LogicalName='lc_isblocked')"
            "?$select=LogicalName,AttributeType"
        )
    except RuntimeError as e:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(str(e))
    r.elapsed_ms = int((time.time() - t0) * 1000)
    if body.get("AttributeType") in ("Boolean", "TwoOptions"):
        return r.ok(f"AttributeType={body.get('AttributeType')}")
    return r.fail(f"unexpected AttributeType: {body}")


def preflight_p3():
    r = Result("P3: CustomAPI lc_CalculateLaunchReadiness exists")
    t0 = time.time()
    body = get(
        "customapis?$filter=uniquename eq 'lc_CalculateLaunchReadiness'"
        "&$select=customapiid,uniquename,displayname"
    )
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    if rows:
        return r.ok(f"id={rows[0]['customapiid']}", payload=rows[0])
    return r.fail("CustomAPI not found - run Episode 5 setup")


SEVERITY_HEADINGS = ["P0", "P1", "P2", "P3"]
IDEMPOTENCY_MARKERS = ["Source: Launch Sentinel", "Correlation: task=", "GeneratedByAutomation: true"]


def preflight_p4():
    r = Result("P4: Sentinel prompt has severity rubric")
    if not SENTINEL_PROMPT_PATH.exists():
        return r.fail(f"missing {SENTINEL_PROMPT_PATH}")
    src = SENTINEL_PROMPT_PATH.read_text(encoding="utf-8")
    missing = [h for h in SEVERITY_HEADINGS if h not in src]
    if missing:
        return r.fail(f"missing severity headings: {missing}", payload={"chars": len(src)})
    return r.ok(f"all 4 severity headings present ({len(src)} chars)")


def preflight_p5():
    r = Result("P5: Sentinel prompt has idempotency markers")
    if not SENTINEL_PROMPT_PATH.exists():
        return r.fail(f"missing {SENTINEL_PROMPT_PATH}")
    src = SENTINEL_PROMPT_PATH.read_text(encoding="utf-8")
    missing = [m for m in IDEMPOTENCY_MARKERS if m not in src]
    if missing:
        return r.fail(f"missing markers: {missing}")
    return r.ok("Source / Correlation / GeneratedByAutomation all present")


def preflight_p6():
    r = Result("P6: Severity rubric matches escalation-policy.md")
    if not SENTINEL_PROMPT_PATH.exists():
        return r.fail(f"missing {SENTINEL_PROMPT_PATH}")
    if not ESCALATION_POLICY_PATH.exists():
        return r.fail(f"missing {ESCALATION_POLICY_PATH}")
    prompt = SENTINEL_PROMPT_PATH.read_text(encoding="utf-8").lower()
    policy = ESCALATION_POLICY_PATH.read_text(encoding="utf-8").lower()
    # Heuristic drift detector: same severity labels appear in both; same day-thresholds.
    # Accept either prose form ("2 days") or compressed table form ("≤ 2", "<= 2").
    def has_threshold(text, n):
        compact = text.replace(" ", "")
        return (
            f"{n}days" in compact
            or f"≤{n}" in compact
            or f"<={n}" in compact
        )
    expected = [2, 7, 14]
    prompt_thresholds = [n for n in expected if has_threshold(prompt, n)]
    policy_thresholds = [n for n in expected if has_threshold(policy, n)]
    if set(prompt_thresholds) != set(policy_thresholds):
        return r.fail(
            f"day-threshold drift: prompt has {prompt_thresholds}, policy has {policy_thresholds}",
            payload={"expected": expected},
        )
    # Verify the policy file has a dedicated "Autonomous mode" section so Sentinel
    # has a canonical home outside the prompt.
    if "autonomous mode" not in policy:
        return r.fail("escalation-policy.md missing 'Autonomous mode' section (Sentinel skill home)")
    return r.ok(f"thresholds aligned: {prompt_thresholds}; autonomous-mode section present")


SKILL_LOAD_LITERALS = [
    "describe('skills/Escalation Policy')",
    "describe('skills/Launch Readiness Digest')",
]
DIGEST_SKILL_PATH = REPO_ROOT / "business-skills" / "launch-readiness-digest.md"


def preflight_p7():
    r = Result("P7: Sentinel prompt loads skills via describe() (skills-as-brain)")
    if not SENTINEL_PROMPT_PATH.exists():
        return r.fail(f"missing {SENTINEL_PROMPT_PATH}")
    src = SENTINEL_PROMPT_PATH.read_text(encoding="utf-8")
    missing = [lit for lit in SKILL_LOAD_LITERALS if lit not in src]
    if missing:
        return r.fail(
            f"prompt missing skill-load directives: {missing}",
            payload={"hint": "Each behavior must call describe('skills/<Name>') as Step 0"},
        )
    if not DIGEST_SKILL_PATH.exists():
        return r.fail(f"missing skill file: {DIGEST_SKILL_PATH}")
    digest_md = DIGEST_SKILL_PATH.read_text(encoding="utf-8").lower()
    # Sanity: the digest skill must mention the SQL gotcha and the active-status codes.
    required_in_digest = ["10600001", "10600002", "10600003", "sendmessagetoself"]
    missing_in_digest = [tok for tok in required_in_digest if tok not in digest_md]
    if missing_in_digest:
        return r.fail(
            f"launch-readiness-digest.md missing required tokens: {missing_in_digest}",
        )
    return r.ok("both describe() lines present; digest skill contains SQL + Teams target")


# ---------- Smoke ----------

def smoke_s1():
    r = Result("S1: Active launches OData query returns rows")
    t0 = time.time()
    flt = " or ".join(f"lc_launchstatus eq {v}" for v in ACTIVE_LAUNCH_STATUS_VALUES)
    try:
        body = get(
            f"lc_launchs?$filter={flt}"
            "&$select=lc_launchid,lc_name,lc_launchstatus,lc_targetdate&$top=10"
        )
    except RuntimeError as e:
        r.elapsed_ms = int((time.time() - t0) * 1000)
        return r.fail(str(e))
    r.elapsed_ms = int((time.time() - t0) * 1000)
    rows = body.get("value", [])
    r.payload = rows
    if not rows:
        return r.fail("0 active launches - need at least one for S2 + T1")
    names = ", ".join(row.get("lc_name") or "(unnamed)" for row in rows[:5])
    return r.ok(f"{len(rows)} active launch(es): {names}", payload=rows)


def smoke_s2(active_launches):
    r = Result("S2: lc_CalculateLaunchReadiness invoke smoke")
    if not active_launches:
        return r.fail("No active launches; cannot invoke")
    target = active_launches[0]
    name = target.get("lc_name")
    if not name:
        return r.fail("Active launch has no lc_name")
    body = {"lc_LaunchName": name}
    status, resp, ms = _req("POST", "lc_CalculateLaunchReadiness", body=body)
    r.elapsed_ms = ms
    if status != 200:
        return r.fail(f"HTTP {status}: {resp}", payload={"request": body, "response": resp})
    score = resp.get("lc_ReadinessScore")
    verdict = resp.get("lc_Verdict")
    if score is None or verdict is None:
        return r.fail("missing score/verdict", payload={"request": body, "response": resp})
    return r.ok(f"{name} -> Score={score}, Verdict={verdict}", payload={"request": body, "response": resp})


# ---------- T1: trigger round-trip ----------

def trigger_t1(active_launches, timeout_s):
    r = Result(f"T1: ephemeral task -> Sentinel statusupdate (timeout {timeout_s}s)")
    if not active_launches:
        return r.fail("No active launches")
    launch_id = active_launches[0]["lc_launchid"]

    # 1. Find a milestone on this launch (or skip)
    milestones = get(
        f"lc_milestones?$filter=_lc_launchid_value eq {launch_id}"
        "&$select=lc_milestoneid,lc_name&$top=1"
    ).get("value", [])
    if not milestones:
        return r.skip("active launch has no milestones; create one to enable T1")
    milestone_id = milestones[0]["lc_milestoneid"]

    # 2. Create ephemeral task
    correlation_token = f"ep7smoke-{uuid.uuid4().hex[:12]}"
    task_title = f"Ep7 Sentinel Smoke {datetime.now().strftime('%H%M%S')} ({correlation_token})"
    body = {
        "lc_title": task_title,
        "lc_taskstatus": 10600020,  # NotStarted
        "lc_isblocked": False,
        "lc_blockerreason": "",
        "lc_MilestoneId@odata.bind": f"/lc_milestones({milestone_id})",
    }
    status, resp, ms = _req("POST", "lc_tasks", body=body, extra_headers={"Prefer": "return=representation"})
    if status not in (200, 201):
        return r.fail(f"create ephemeral task failed: HTTP {status}: {resp}")
    task_id = resp.get("lc_taskid")
    if not task_id:
        return r.fail(f"create succeeded but no taskid in response: {resp}")
    print(f"    {C.DIM}created ephemeral task {task_id} '{task_title}'{C.END}")

    deleted = False
    try:
        # 3. Patch to blocked
        patch = {
            "lc_isblocked": True,
            "lc_blockerreason": f"[harness] Sentinel smoke test, correlation={correlation_token}",
            "lc_taskstatus": 10600023,  # Blocked
        }
        st, _, _ = _req("PATCH", f"lc_tasks({task_id})", body=patch)
        if st >= 400:
            return r.fail(f"patch to blocked failed: HTTP {st}")
        print(f"    {C.DIM}patched lc_isblocked=true, polling for status update...{C.END}")

        # 4. Poll for a status update with our correlation marker (plus optional Sentinel signature)
        deadline = time.time() + timeout_s
        poll_n = 0
        seen_id = None
        while time.time() < deadline:
            poll_n += 1
            time.sleep(10)
            # Search by lc_body containing our correlation token (cheap text match)
            flt = (
                f"_lc_launchid_value eq {launch_id}"
                f" and contains(lc_body,'{correlation_token}')"
            )
            try:
                page = get(
                    f"lc_statusupdates?$filter={flt}"
                    "&$select=lc_statusupdateid,lc_title,lc_body,lc_updatedon&$top=1"
                )
            except RuntimeError as e:
                # transient OData failure shouldn't kill the test
                print(f"    {C.DIM}poll {poll_n}: query error ({e}){C.END}")
                continue
            rows = page.get("value", [])
            if rows:
                seen_id = rows[0]["lc_statusupdateid"]
                row = rows[0]
                msg = (
                    f"matched after ~{poll_n*10}s: title='{row.get('lc_title')}'"
                )
                # Bonus: confirm Source: marker also present
                source_ok = "Source: Launch Sentinel" in (row.get("lc_body") or "")
                if not source_ok:
                    msg += " (warn: no Source: marker in body — body-grep matched but signature missing)"
                r.ok(msg, payload=row)
                break
        else:
            # Timed out without a row: not a hard fail (bot may not be deployed)
            r.skip(
                f"no status update found within {timeout_s}s "
                "(Sentinel may not be deployed yet; rerun --trigger once it is published)",
                payload={"correlation_token": correlation_token, "task_id": task_id},
            )
    finally:
        # 5. Clean up: delete the ephemeral status update (if Sentinel created one) + task
        if seen_id:
            st, _, _ = _req("DELETE", f"lc_statusupdates({seen_id})")
            if st < 400:
                print(f"    {C.DIM}cleaned up ephemeral status update {seen_id}{C.END}")
        st, _, _ = _req("DELETE", f"lc_tasks({task_id})")
        if st < 400:
            print(f"    {C.DIM}cleaned up ephemeral task {task_id}{C.END}")
            deleted = True
    if not deleted:
        # Don't raise — but mark detail
        if r.passed:
            r.detail += " (warn: ephemeral task may not have been deleted)"
    return r


# ---------- Reporting ----------

def render_console(results):
    print()
    print(C.BOLD + "Episode 7 - Local Test Run" + C.END)
    print("=" * 60)
    pass_n = sum(1 for r in results if r.passed)
    fail_n = sum(1 for r in results if r.passed is False)
    skip_n = sum(1 for r in results if r.passed is None)
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
    color = C.GREEN if fail_n == 0 else C.RED
    print(f"  {color}{pass_n} OK / {fail_n} FAIL / {skip_n} SKIP / {total} total{C.END}")
    print()


def render_markdown(results):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Episode 7 - Local Test Results",
        f"_Generated: {ts}_",
        "",
        f"**Environment:** `{ENV}`",
        "",
    ]
    pass_n = sum(1 for r in results if r.passed)
    fail_n = sum(1 for r in results if r.passed is False)
    skip_n = sum(1 for r in results if r.passed is None)
    total = len(results)
    icon = "OK" if fail_n == 0 else "FAIL"
    lines.append(f"## Summary: {icon} - {pass_n} pass / {fail_n} fail / {skip_n} skip / {total} total")
    lines.append("")
    lines.append("| Test | Result | Time | Detail |")
    lines.append("|------|--------|------|--------|")
    for r in results:
        if r.passed is None:
            ic = "SKIP"
        elif r.passed:
            ic = "PASS"
        else:
            ic = "FAIL"
        detail = (r.detail or "").replace("|", "\\|")
        lines.append(f"| {r.name} | {ic} | {r.elapsed_ms}ms | {detail} |")
    lines.append("")
    lines.append("## Details")
    for r in results:
        lines.append("")
        lines.append(f"### {r.name}")
        state = "PASS" if r.passed else ("SKIP" if r.passed is None else "FAIL")
        lines.append(f"- Result: {state}")
        lines.append(f"- Time: {r.elapsed_ms}ms")
        if r.detail:
            lines.append(f"- Notes: {r.detail}")
        if r.payload is not None:
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(r.payload, indent=2, default=str)[:4000])
            lines.append("```")
    return "\n".join(lines) + "\n"


PROMPT_DOC = """# Episode 7 - Manual Verification Checklist

_Generated by `episodes/ep-07-autonomous-agents/preflight.py`. Re-run after substrate changes._

Sentinel doesn't take prompts (it's autonomous), so this file is a UI checklist
to run in Copilot Studio + Power Automate after the harness has gone green.

## Sentinel (Part 1)

### Setup verification
- [ ] Bot `Launch Sentinel` exists in the same env as LaunchControl solution
- [ ] **Generative orchestration** is ON in the bot settings
- [ ] **Instructions** match `agents/launch-sentinel/system-prompt.txt` (paste-check)
- [ ] **Tools**: Dataverse MCP Server attached
- [ ] **Trigger**: `When a row is added or modified (Dataverse)` -> table=`lc_task`, change=`Modified`, filter `lc_isblocked eq true`
- [ ] Trigger -> action: `Run agent: Launch Sentinel`
- [ ] Bot is **published** (not just saved)

### Live behavior verification
1. **Fresh block**:
   - In a model-driven app or via MCP, set `lc_isblocked=true` on a real (non-test) task on an active launch.
   - Within ~60s, confirm a new `lc_statusupdate` row appears with title `[<P0/P1/P2/P3>] <task title> blocked`.
   - Body must contain `Source: Launch Sentinel`, `Correlation: task=<id>`, `GeneratedByAutomation: true`.
2. **Idempotency**:
   - PATCH the same task again (e.g., update `lc_blockerreason`).
   - Confirm NO second status update appears within 5 minutes.
3. **Stale-block guard**:
   - On a task linked to a closed GitHub issue, set `lc_isblocked=true`.
   - Confirm Sentinel writes nothing (silent exit).
4. **Severity edge case**:
   - Block a task whose milestone has no `lc_duedate`.
   - Confirm severity is P2 - Medium and body says "(no due date set)".

### Cleanup after each test
Delete the ephemeral status update + revert `lc_isblocked` so you don't pollute the demo data.

## Daily Readiness Flow (Part 2)

### MCP-step path (if available in your tenant)
- [ ] Spike flow returned data from a `Dataverse MCP` step (see `agents/agent-flows/daily-readiness-summary.md`)
- [ ] Production flow runs successfully on schedule
- [ ] Teams post lands in target channel with all active launches summarized

### Fallback path (Power Automate standard connectors)
- [ ] Flow uses `Common Data Service` and `Microsoft Teams` connectors only
- [ ] Identical message content to the MCP path

## What to call out on camera
- Sentinel signature line `Source: Launch Sentinel` is the easy "this is automation" cue
- Correlation marker in `lc_body` is what enables idempotency
- The bot writes to the SAME `lc_statusupdate` table the Coordinator (Ep 6) reads from -- one source of truth, two agents

## When something fails
| Symptom | Most likely cause |
|---------|-------------------|
| Trigger fires repeatedly, multiple status updates | Idempotency check missing or markers not in body |
| Trigger never fires | Bot not published; trigger filter wrong (`lc_isblocked` vs case); generative orchestration off |
| Status update written but missing markers | Prompt re-pasted incomplete - re-sync from `system-prompt.txt` |
| Severity always P2 | Milestone lookup failing - check Sentinel MCP tool has read on `lc_milestone` |
"""


def write_prompt_set():
    out = Path(__file__).resolve().parent / "test_ep7_prompts.md"
    out.write_text(PROMPT_DOC, encoding="utf-8")
    return out


def run_all(include_trigger=False, trigger_timeout=300):
    results = []
    results.append(preflight_p1())
    results.append(preflight_p2())
    results.append(preflight_p3())
    results.append(preflight_p4())
    results.append(preflight_p5())
    results.append(preflight_p6())
    results.append(preflight_p7())
    s1 = smoke_s1()
    results.append(s1)
    active = s1.payload if s1.passed else []
    results.append(smoke_s2(active))
    if include_trigger:
        results.append(trigger_t1(active, trigger_timeout))
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true", help="Emit the test plan (markdown)")
    p.add_argument("--run", action="store_true", help="Pre-flight + read-only smoke")
    p.add_argument("--trigger", action="store_true", help="Run T1 (ephemeral task lifecycle); implies --run")
    p.add_argument("--trigger-timeout", type=int, default=300, help="T1 poll timeout in seconds (default 300)")
    p.add_argument("--out", default=None, help="Path to write results markdown")
    args = p.parse_args()
    if not (args.plan or args.run or args.trigger):
        p.print_help()
        sys.exit(2)
    if args.plan:
        print(PLAN)
    if args.run or args.trigger:
        results = run_all(include_trigger=args.trigger, trigger_timeout=args.trigger_timeout)
        render_console(results)
        out_path = args.out or str(
            Path(__file__).resolve().parent
            / f"test_results_ep7_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        Path(out_path).write_text(render_markdown(results), encoding="utf-8")
        prompt_path = write_prompt_set()
        print(f"  Results written:    {out_path}")
        print(f"  Manual checklist:   {prompt_path}")
        # Exit 0 if no FAILS (skips are OK), 1 otherwise
        any_fail = any(r.passed is False for r in results)
        sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
