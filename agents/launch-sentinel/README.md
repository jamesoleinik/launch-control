# Launch Sentinel — Autonomous Agent (Episode 7)

`Launch Sentinel` is an **autonomous** Copilot Studio agent. Unlike the conversational Launch Coordinator (Ep 6), Sentinel never chats. It runs on **two triggers**, both bound to the same agent and the same Dataverse MCP server:

1. **Event trigger** — `lc_task` updated with `lc_isblocked = true` → write ONE escalation `lc_statusupdate` row.
2. **Recurrence trigger** — Mon–Fri 08:00 → post ONE readiness digest to the bot's Teams **Notes to Self** chat.

The system prompt (`system-prompt.txt`) splits these as **Behavior 1** and **Behavior 2** and uses the trigger payload shape as the discriminator (presence of `lc_taskid` → Behavior 1; empty/timestamp-only payload → Behavior 2).

This README documents how to set up the bot in the Copilot Studio UI. Autonomous event triggers, recurrence triggers, and Dataverse event subscriptions are not currently available through the M365 Agents Toolkit / declarative-agent path used in Ep 6.

---

## What it does

```
┌──────────────────────────┐    update where      ┌────────────────────┐
│  lc_task row             │  lc_isblocked=true   │ Launch Sentinel    │  ── Behavior 1 ──► lc_statusupdate row
│  (any task gets blocked) │ ──────────────────── │ (autonomous)       │
└──────────────────────────┘                      │                    │
                                                  │   one agent        │
┌──────────────────────────┐    Mon-Fri 08:00     │   two triggers     │
│  Recurrence              │ ──────────────────── │   one Dataverse    │  ── Behavior 2 ──► Teams "Notes to Self"
│  (no payload)            │                      │   MCP server       │
└──────────────────────────┘                      └────────────────────┘
```

---

## Why a separate bot (vs. extending the Launch Coordinator)

- **Single responsibility** — one trigger, one action. Easier to reason about, observe, and disable.
- **No prompt bleed** — the conversational agent's tools and guardrails don't get confused by the autonomous path.
- **Independent ALM** — Sentinel can be paused or rolled back without affecting the chat experience.

---

## Source of truth

- **Prompt**: `agents/launch-sentinel/system-prompt.txt` ← copy/paste into the bot's Instructions
- **Behavior 1 brain**: `business-skills/escalation-policy.md` (the "Autonomous mode (Launch Sentinel)" section). Sentinel loads this skill at runtime via Dataverse MCP `describe('skills/Escalation Policy')`.
- **Behavior 2 brain**: `business-skills/launch-readiness-digest.md`. Sentinel loads it via `describe('skills/Launch Readiness Digest')`.
- **Inline FALLBACK** in `system-prompt.txt`: same rubric, SQL, and templates duplicated under labeled FALLBACK headings — used only if `describe()` fails. Belt-and-suspenders so a flaky network never produces a wrong row.

### Skills as the brain

```
                       Dataverse (system of record)
                       ┌──────────────────────────────┐
                       │ skills/Escalation Policy     │ ◄── edit here, both
                       │   • Interactive mode (Coord) │     agents change.
                       │   • Autonomous mode (Sent.)  │     No redeploy.
                       │ skills/Launch-Readiness-Dig. │
                       └──────────────┬───────────────┘
                                      │ describe() at runtime
                                      ▼
       ┌────────────────────┐                  ┌────────────────────┐
       │ Launch Coordinator │                  │ Launch Sentinel    │
       │ (Ep 6, interactive)│                  │ (Ep 7, autonomous) │
       │ uses Esc.Policy    │                  │ B1 → Esc.Policy    │
       │ for chat triage    │                  │ B2 → Readiness Dig.│
       └────────────────────┘                  └────────────────────┘
```

Same `Escalation-Policy` skill backs both the interactive Coordinator (Ep 6) and the autonomous Sentinel (Ep 7) — proof that **business skills are agent-portable**. Edit the markdown in Dataverse and both agents pick up the new policy on their next `describe()`.

### Why fallback (and not strict skill-only)

Strict skill-only would mean Sentinel exits on every transient `describe()` failure — fine for a chat agent, painful for an autonomous one that fires on real events. The FALLBACK keeps the bot working when Dataverse is briefly unavailable; the on-camera demo verifies the trace shows the `describe()` call so viewers see the skill being consulted, not the fallback.

If the policy changes, the canonical edit happens in `business-skills/escalation-policy.md` (the markdown that gets uploaded to Dataverse as the `Escalation-Policy` skill). The inline FALLBACK in `system-prompt.txt` should be re-synced when the skill changes; harness check P7 greps the prompt for the `describe('skills/...')` lines so the skill-load step doesn't silently disappear.

---

## Set up the bot in Copilot Studio (UI)

> **Prerequisite**: you have publish rights in the same environment as the LaunchControl solution (the demo env: `https://YOUR-ORG.crm.dynamics.com/`).

1. **Create the bot**
   - Copilot Studio → **Agents** → **+ New agent**
   - Name: `Launch Sentinel`
   - Description: `Autonomous escalation for blocked launch tasks`
   - Skip the conversational starter prompts.

2. **Set instructions**
   - Open the new agent → **Overview** → **Instructions**
   - Paste the entire content of `agents/launch-sentinel/system-prompt.txt`
   - Save.

3. **Attach the Dataverse MCP server as a tool**
   - **Tools** → **+ Add tool** → **Model Context Protocol** → **Dataverse MCP Server**
   - Confirm the connection is to the same env as the bot.
   - Enable: read on `lc_task`, `lc_milestone`, `lc_launch`, `lc_teammember`, `lc_statusupdate`; create on `lc_statusupdate`. The unbound action `lc_CalculateLaunchReadiness` is auto-exposed once the MCP tool is attached — no separate registration needed.
   - **Generative orchestration**: ON (required for the bot to chain MCP calls and to dispatch by trigger payload shape).

4. **Attach the Teams MCP server as a tool (for Behavior 2 only)**
   - **Tools** → **+ Add tool** → **Model Context Protocol** → **Work IQ Teams MCP server** (or the equivalent Teams MCP tool name in your tenant).
   - Enable only the **`SendMessageToSelf`** action. Disable `SendMessageToUser`, `SendMessageToChat`, `SendMessageToChannel`, etc. — Behavior 2 only ever posts to the bot's own Notes to Self chat. Keeping the surface narrow prevents the LLM from wandering on the digest path.

5. **Create the event-driven trigger (Behavior 1)**
   - **Triggers** → **+ New trigger** → **Event-driven** → **When a row is added or modified (Dataverse)**
   - **Table**: `lc_task`
   - **Change type**: `Modified`
   - **Filter rows**: `lc_isblocked eq true`
   - **Connection**: a human-owned demo connection (NOT a service principal in this env — Sentinel needs row-level read on related tables).
   - **Run as**: connection owner.
   - Bind the action to `Run agent: Launch Sentinel`. Pass the modified task row as input.

6. **Create the recurrence trigger (Behavior 2)**
   - **Triggers** → **+ New trigger** → **Recurrence / On a schedule**.
   - **Frequency**: Day. **Days of week**: Mon, Tue, Wed, Thu, Fri. **Time**: 08:00. **Time zone**: your local TZ.
   - Bind the action to `Run agent: Launch Sentinel`. Pass **no payload** — the empty payload is what tells the system prompt this is a Behavior 2 invocation.

7. **Publish**
   - **Publish** → confirm scope.
   - Both triggers go live within ~60 seconds of publish (subject to backend cadence).

> **Why two triggers on one agent (and not a separate scheduled Agent Flow):** during build we tried Behavior 2 as a standalone Agent Flow with Dataverse MCP steps. The preview MCP-step UX could not reliably invoke Custom APIs from natural-language Instructions, so we collapsed the digest into Sentinel as a second trigger. Tighter narrative anyway: **one agent, multiple triggers, same Dataverse MCP server.** The deferred standalone-flow design is preserved at [`../agent-flows/daily-readiness-summary.md`](../agent-flows/daily-readiness-summary.md) for when the MCP-step UX hardens.

---

## Known caveats (be honest in the demo)

| # | Caveat | Mitigation |
|---|--------|-----------|
| 1 | The trigger fires on every modify where `lc_isblocked eq true`, not only on the false→true transition. | Idempotency check in the prompt (`Correlation: task=<id>` marker + 24h cooldown). |
| 2 | The bot runs under the trigger connection's identity. Status updates are authored by that user. | Document this; use a demo "Launch Bot Service" account in real deployments. |
| 3 | Trigger latency is tenant-dependent. In this env it typically lands within 10–60 seconds. | For recording, capture a real run as B-roll; do NOT promise live latency on camera. |
| 4 | Autonomous bots and event triggers are configured in the UI and **are not currently exportable** via the same solution path used in Ep 6. | Episode framing: "this is the UI-built ALM gap; we'll export topics + instructions but not the trigger binding." |
| 5 | If the Dataverse MCP server tool calls fail for any reason, the bot exits silently. | Trade-off: prefer "no row" to "bad row." |
| 6 | The recurrence trigger fires the agent without payload. The system prompt's behavior dispatcher is the LLM, not a deterministic switch. | Behavior 2 narrows the prompt to one SQL query + one Custom API + one Teams call to keep the LLM on-rails; harness check P7 (TBD) will grep the prompt for the "ONLY this query" lock. |
| 7 | The Teams MCP `SendMessageToSelf` action posts to whichever identity the Teams connection authenticated as. | Use a dedicated demo account when recording so the Notes to Self chat shown on screen is the right one. |

---

## Expected behavior matrix

### Behavior 1 (event trigger)

| Scenario | Sentinel does |
|----------|---------------|
| Task unblocked → blocked, milestone in 1 day | Writes `[P0 - Critical] <title> blocked`, with assignee + reason. |
| Same task remains blocked, trigger fires again 5 min later | **No-op** (idempotency). |
| Same task still blocked 25h later | Writes `[P0 - Critical] <title> still blocked (follow-up)`. |
| Task blocked but linked GitHub issue is `closed` | **No-op** (stale-block guard). |
| Task blocked on a launch in `Launched` or `OnHold` status | **No-op**. |
| Task blocked, milestone has no due date | Writes `[P2 - Medium]` with `(no due date set)` in body. |
| MCP tool returns 5xx | **No-op** (silent failure preferred over wrong row). |

### Behavior 2 (recurrence trigger)

| Scenario | Sentinel does |
|----------|---------------|
| Recurrence fires, ≥1 active launch | Posts `# Launch Readiness — <date>` digest to Notes to Self with one block per launch (Decision, Score, Target, BlockerCount, AtRiskMilestoneCount). |
| Recurrence fires, zero active launches | Posts `Launch Readiness — <date>: no active launches.` (single line). |
| `lc_CalculateLaunchReadiness` fails for one launch | Continues; that launch's block shows `Decision=ERROR, Score=?` so the reader sees it was checked. |
| Teams MCP `SendMessageToSelf` fails | **No-op** (silent failure; tomorrow's run covers it). |
| Agent goes off-script and queries `lc_task` / `lc_milestone` directly | Should not happen — the prompt locks Behavior 2 to one SQL query. If you observe this, re-paste the prompt and republish. |

---

## Testing

Run the substrate harness before recording:

```bash
python episodes/ep-07-autonomous-agents/preflight.py --plan      # show what gets checked
python episodes/ep-07-autonomous-agents/preflight.py --run       # full pre-flight + non-destructive smoke
python episodes/ep-07-autonomous-agents/preflight.py --trigger   # ephemeral task lifecycle (T1)
```

The harness verifies:
- Schema check on `lc_statusupdate` (must have `lc_title`, `lc_body`, `lc_updatedon`, `_lc_launchid_value`)
- `lc_task.lc_isblocked` column exists
- Severity rubric strings present in `system-prompt.txt`
- `Correlation:` and `Source: Launch Sentinel` markers present in `system-prompt.txt`
- `lc_CalculateLaunchReadiness` Custom API exists (used by Coordinator + Flow)
- (T1, optional) creates ephemeral test task → flips `lc_isblocked=true` → polls for the resulting status update by correlation marker → cleans up.

T1 is destructive on its own ephemeral row only. It will not modify any pre-existing task.
