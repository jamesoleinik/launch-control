# Episode 9 — Autonomous Agents

**Status:** ✅ Built · 🎬 Not yet recorded
**Features:** ⭐ Copilot Studio autonomous agent · ⭐ Event triggers + Recurrence triggers on a single agent · ⭐ Dataverse MCP + Teams MCP composed in one bot
**Layer:** 🔵 Layer 2 (proactive automation)
**Coding agent:** Copilot Studio UI (low-code; Sentinel is one autonomous agent with two trigger types)
**Runtime:** Copilot Studio autonomous bot · Dataverse MCP Server (Preview) + Teams MCP `SendMessageToSelf`

---

## The hook

> _"Episode 8's agent answers when you ask. This one acts without you asking. Every time a task gets blocked. Every morning at 8 AM. Same agent. Same data."_

Episode 8 made Dataverse conversational. Episode 9 makes it **proactive** — and shows how a single autonomous agent, bound to the **same Dataverse MCP server**, can act on **two completely different trigger types** without spinning up a second surface.

1. **Behavior 1 — Event-driven escalation.** A Dataverse row event (`lc_task.lc_isblocked` flips to `true`) fires Sentinel. It classifies severity, writes a structured `lc_statusupdate` row signed `Source: Launch Sentinel`, and goes silent for 24h on the same task.
2. **Behavior 2 — Scheduled readiness digest.** A recurrence trigger (Mon–Fri 08:00) fires the same agent with no payload. Sentinel queries active launches via the Dataverse MCP `read_query` tool, scores each one with `lc_CalculateLaunchReadiness`, formats a markdown digest, and posts to its Teams **Notes to Self** chat via the Teams MCP server.

The system prompt uses the trigger payload shape as the discriminator (presence of `lc_taskid` → Behavior 1; empty payload → Behavior 2). **One agent. Two triggers. One Dataverse MCP server.** That's the punch line.

Behavior 1 produces rows in the same `lc_statusupdate` table the Coordinator (Episode 8) reads from. Behavior 2 routes to Teams. Same agent, two effectors, both autonomous.

---

## The narrative beat

```
[task PATCH lc_isblocked=true]
    ▼
Copilot Studio trigger fires
    ▼
Launch Sentinel (autonomous)
    ├── Lookup chain: task → milestone → launch (skip if launch not active)
    ├── Severity rubric (P0/P1/P2/P3 by milestone duedate days)
    ├── Idempotency check (Correlation marker + 24h cooldown)
    ├── Stale-block guard (linked GitHub issue closed → no-op)
    ▼
Write lc_statusupdate
    title: "[P1] Security Review blocked"
    body:  Source: Launch Sentinel
           Correlation: task=<guid>
           GeneratedByAutomation: true
           ...severity reasoning, suggested next step...
```

```
[Mon–Fri 08:00 recurrence]
    ▼
Same Launch Sentinel agent fires (no payload)
    ▼
Prompt's discriminator: empty payload → Behavior 2
    ▼
Dataverse MCP read_query (raw SQL):
    SELECT lc_launchid, lc_name, lc_launchstatus, lc_targetdate
    FROM lc_launch
    WHERE lc_launchstatus IN (10600001, 10600002, 10600003)
    ▼
For each active launch:
    invoke lc_CalculateLaunchReadiness (Custom API from Ep 5)
    via the same Dataverse MCP server
    ▼
Compose markdown digest
    ▼
Teams MCP SendMessageToSelf → Notes to Self chat
```

---

## One agent, two triggers — why we collapsed Part 2 into Sentinel

The original plan for Episode 9 had **two surfaces** in the autonomous tier: Sentinel (event-driven bot) and a **separate scheduled Agent Flow** with Dataverse MCP steps that posted the digest. The framing was "MCP tools and MCP flow steps are the same primitive."

We built it. It almost worked. The blocker was the preview MCP-step UX in Agent Flows: the natural-language Instructions box reliably accepts raw Dataverse SQL, **but** it could not reliably invoke unbound Custom APIs (like `lc_CalculateLaunchReadiness`) from natural language — the call would silently fail with "An error has occurred" or invoke the wrong tool. Not something you ship on camera.

The fix was simple. **Add a recurrence trigger directly to Sentinel.** The agent already had Dataverse MCP attached as a tool, generative orchestration on, and a Custom API auto-exposed by the MCP server. Adding a second trigger and the Teams MCP server (one tool — `SendMessageToSelf`) gave us the digest with no second surface to maintain.

Tighter narrative, less surface area, same MCP punch line — just expressed as **"one agent, multiple triggers"** instead of "two surfaces, one MCP server."

The standalone Agent Flow design is preserved at [`agents/agent-flows/daily-readiness-summary.md`](../../agents/agent-flows/daily-readiness-summary.md) (with a deferred banner at the top) so we can revisit when the MCP-step UX hardens.

---

## Behavior 1 — event-driven escalation

### Why a separate agent (not "extend the Coordinator")

The Coordinator is a chat agent: humans in the loop, every turn is consented.
Sentinel runs without a human and writes to Dataverse on its own authority.
Different identity model, different guardrails, different prompt. Mixing them
into one bot would couple two failure modes.

### What's in the prompt (skill-loaded, with inline FALLBACK)

The full prompt lives in [`agents/launch-sentinel/system-prompt.txt`](../../agents/launch-sentinel/system-prompt.txt). It runs in two stages:

**Step 0 — load the skill.** The first instruction in each behavior block is `describe('skills/<name>')` against the Dataverse MCP server. For Behavior 1 it loads `Escalation-Policy`; for Behavior 2 it loads `Launch-Readiness-Digest`. The skill is the canonical source for the lookup chain, severity rubric, and `lc_statusupdate` body template (B1) — or the locked SQL, Custom API loop, and digest template (B2).

**Inline FALLBACK.** Below each Step 0 the prompt duplicates the same rubric, SQL, and templates under `## FALLBACK` headings. The agent only reads them if `describe()` fails. This is belt-and-suspenders: the bot keeps working when Dataverse is briefly unreachable, but the on-camera demo shows the trace calling `describe()` first — so viewers see the skill being consulted.

The skill files are the source of truth:

- [`business-skills/escalation-policy.md`](../../business-skills/escalation-policy.md) — has both an **Interactive mode** section (used by the Coordinator agent in Ep 8) and an **Autonomous mode (Launch Sentinel)** section (used by Sentinel B1). Same skill, two consumers, proving skills are agent-portable.
- [`business-skills/launch-readiness-digest.md`](../../business-skills/launch-readiness-digest.md) — new in this episode, owns Sentinel B2.

The mandatory provenance markers (`Source: Launch Sentinel`, `Correlation: task=<id>`, `GeneratedByAutomation: true`) live in the skill, not the prompt. Edit the skill in Dataverse → both the canonical reference and the agent's behavior change. No bot redeploy.

### Setup

See [`agents/launch-sentinel/README.md`](../../agents/launch-sentinel/README.md) for the full UI clickpath. Summary:

1. New Copilot Studio bot **Launch Sentinel**, generative orchestration ON
2. Paste `system-prompt.txt` into Instructions (whole file, no edits — fits under the 8000-char limit)
3. Tools → add Dataverse MCP Server (Preview) → enable `lc_task`, `lc_milestone`, `lc_launch`, `lc_teammember`, `lc_statusupdate` permissions; Custom API `lc_CalculateLaunchReadiness` is auto-exposed
4. Triggers → **Event-driven** → "When a row is added or modified (Dataverse)" → table=`lc_task`, change=`Modified`, filter=`lc_isblocked eq true` → action: Run agent
5. Publish

---

## Behavior 2 — scheduled readiness digest

Behavior 2 lives on the **same agent**. Same instructions file. Same Dataverse MCP server. The recurrence trigger is just a second binding.

### What's different from Behavior 1

- **No identity derivation, no severity, no Dataverse writes.** The digest is read-only on Dataverse.
- **One SQL query, locked.** The prompt instructs the agent to run exactly one `read_query` against `lc_launch` and forbids querying `lc_task` / `lc_milestone` / `lc_statusupdate` (the Custom API already aggregates the counts the digest needs). This was the fix for an early failure where the LLM tried to enrich the digest with task-level detail and produced an invalid OData-style column name in SQL.
- **Custom API does the heavy lifting.** `lc_CalculateLaunchReadiness` (built in Ep 5) returns Score, Decision, BlockerCount, AtRiskMilestoneCount per launch. The agent just unpacks and formats — no business logic in the prompt.
- **Teams MCP, not Dataverse, is the effector.** The agent calls `SendMessageToSelf` on the Teams MCP server. The digest never touches `lc_statusupdate` — keeping that table reserved for Behavior 1 and the Coordinator's human-authored updates.

### Setup additions on top of Behavior 1

1. Tools → add **Teams MCP server** (Work IQ) → enable **only** `SendMessageToSelf`. Disable everything else to keep the LLM on-rails.
2. Triggers → **Recurrence** → Days: Mon–Fri, Time: 08:00, TZ: local → action: Run agent (no payload — empty payload is the discriminator).
3. Republish.

### Why this works without a separate scheduled flow

The original two-surface design depended on the MCP-step type in Agent Flows being able to invoke unbound Custom APIs from natural language. In the current preview that path is unreliable. By binding both triggers to a single agent that already has the Dataverse MCP tool, we get:

- the recurrence behavior (cron-driven, deterministic-enough)
- without losing the MCP narrative (the agent still resolves everything through MCP)
- and without the deployment overhead of a second surface
- *plus* a tighter punch line: **same agent, different triggers, all MCP**.

---

## What's NOT in this episode (caveats up front)

- **No public API for trigger bindings.** Both trigger configurations (event and recurrence) are UI-only inside Copilot Studio; we **cannot** solution-export them. Sentinel itself can be packaged into the `LaunchAgents` solution as Instructions + Topics, but both triggers and the Teams MCP connection have to be re-bound by hand in any new environment. Documented at the top of `agents/launch-sentinel/README.md`.
- **No latency SLA on the event trigger.** Trigger latency is "soon, usually within seconds, but not guaranteed." For demos, expect 10–60s between PATCH and status update.
- **Identity caveat.** Both triggers run as the connection owner, not OBO of the user who modified the task or invoked the schedule. Status updates and Notes-to-Self posts appear authored by the trigger connection's user. Recommend a dedicated demo connection for both.
- **No standalone scheduled Agent Flow in this episode.** We tried it; the preview MCP-step UX could not reliably invoke Custom APIs from natural language. The deferred design is preserved at `agents/agent-flows/daily-readiness-summary.md` for future revisitation. **Don't fall back to a Power Automate cloud flow on camera** — different surface, different ALM story, dilutes the MCP narrative.
- **Behavior dispatcher is the LLM, not a deterministic switch.** Both triggers fire the same agent and the prompt picks the behavior by inspecting payload shape. This is by design (showcases generative orchestration) but means an off-script run is theoretically possible. The "ONLY this query" lock in Behavior 2 mitigates this; if you see the bot wandering, re-paste and republish the prompt.

---

## Local validation

`episodes/ep-09-autonomous-agents/preflight.py` is the substrate harness:

```
python episodes/ep-09-autonomous-agents/preflight.py --plan          # show test plan
python episodes/ep-09-autonomous-agents/preflight.py --run           # P1-P6 + S1-S2 (read-only)
python episodes/ep-09-autonomous-agents/preflight.py --trigger       # adds T1 (creates ephemeral task, polls, cleans up)
```

- **P1–P6**: schema + Custom API + prompt-shape + drift detection
- **S1–S2**: read-only smoke against a real active launch
- **T1**: creates `Ep7 Sentinel Smoke <ts>` on a real milestone, sets
  `lc_isblocked=true`, polls `lc_statusupdates` for the correlation marker
  for `--trigger-timeout` seconds (default 300), then DELETES both rows.
  If no row appears in time, T1 is **SKIPPED** (not failed) — meaning the
  bot likely isn't published yet.

Manual UI checklist regenerated each run at `episodes/ep-09-autonomous-agents/prompts.md`.

---

## Recording fallback plan

Live trigger latency is not guaranteed. If the demo run takes too long on
camera:

- **B-roll**: pre-record a 30s clip of the trigger firing into a status
  update appearing in the model-driven app. Cut to it after the PATCH.
- **Show the marker**: zoom into the `lc_body` `Source: Launch Sentinel`
  line — that's the visual cue that "this row was written by automation,
  not a human."
- **Show the cooldown**: PATCH the task again mid-recording, point at the
  status update list, narrate "no second row — that's idempotency in
  action, by design."

For the digest, manually fire the recurrence trigger (or temporarily set frequency to "every 5 minutes" and wait one tick) before recording so a fresh Notes-to-Self post is visible when you cut to that beat.

---

## Files added this episode

```
agents/launch-sentinel/
├── system-prompt.txt                # Behavior 1 + Behavior 2 (single agent, ≤8000 chars)
└── README.md                        # UI setup steps for both triggers + caveats matrix

agents/agent-flows/
└── daily-readiness-summary.md       # DEFERRED — original standalone-flow design (preserved for future)

episodes/ep-09-autonomous-agents/
├── README.md                        # This file
├── preflight.py                     # Substrate harness (P1–P6 + S1–S2 + optional T1)
└── prompts.md                       # Manual UI checklist (regenerated by --plan)
```

No schema changes, no new tables, no new Custom APIs. The whole episode is configuration on top of the substrate Episodes 1–6 already built — plus a second trigger and a second MCP server bound to an existing agent.

---

## What this proves

- The same `lc_statusupdate` table can serve **both** human-authored Coordinator updates and machine-authored Sentinel escalations — the `Source:` marker discriminates at read time.
- **Skills are the brain of an autonomous agent.** Sentinel calls `describe('skills/Escalation Policy')` and `describe('skills/Launch Readiness Digest')` at the start of every run. Edit the markdown in Dataverse and the agent's behavior changes on the next trigger — no bot redeploy.
- **Same skill, two agents.** `Escalation-Policy` is consumed by the interactive Launch Coordinator (Ep 8, "Interactive mode" section) AND the autonomous Launch Sentinel (Ep 9, "Autonomous mode" section). One source of policy, two completely different runtime shapes. That's the skills-portability claim made concrete.
- A **single autonomous agent** can carry **multiple trigger types** (event + recurrence) and **multiple MCP servers** (Dataverse + Teams) without becoming a chat agent. The dispatcher is the prompt itself.
- The MCP punch line is **stronger** when expressed as "same agent, different triggers, all MCP" than as "two surfaces, one MCP server" — fewer moving parts, tighter story, easier to operate.

> **On-camera moment to capture:** open the Sentinel trace log after a B1 fire and point at the `describe('skills/Escalation Policy')` call sitting above the `lc_statusupdate` create. That single line is the entire "skills as the brain" thesis in one screenshot.

---

## Next up

**Episode 10 — The Code-First Agent.** Same skills. Same Dataverse. Same
Custom API. But now the runtime is ~250 lines of Python — GitHub Copilot SDK
as the brain, Microsoft Agent Framework as the abstraction, the Dataverse
MCP server (stdio) as the tool surface. Edit the skill in Dataverse; the
chat agent (Ep 8), the autonomous agent (Ep 9), **and** the Python agent
(Ep 10) all change behavior on their next run. Skills portability, proven
by three different runtimes.
