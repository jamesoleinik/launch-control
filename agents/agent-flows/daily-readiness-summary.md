> ## ⚠️ DEFERRED — see [`docs/episodes/episode-7.md`](../../docs/episodes/episode-7.md)
>
> The standalone Agent Flow surface was pivoted out of Episode 7 because the preview Dataverse MCP-step UX could not reliably invoke unbound Custom APIs (specifically `lc_CalculateLaunchReadiness`) from natural-language Instructions. We discovered the Instructions box does accept raw Dataverse SQL (preserved in Step 0 / Step 1 below), but Custom API invocation in nested loop steps was the unblockable issue.
>
> **Replacement:** a recurrence trigger added directly to the Launch Sentinel autonomous agent. Same Dataverse MCP server, plus a Teams MCP `SendMessageToSelf` action. See [`agents/launch-sentinel/README.md`](../launch-sentinel/README.md) and [`docs/episodes/episode-7.md`](../../docs/episodes/episode-7.md).
>
> **Why this doc is preserved:** when the MCP-step UX in Agent Flows hardens (Custom API invocation becomes reliable from the Instructions box), this design is still the cleanest expression of "MCP tools and MCP flow steps are the same primitive." Reactivate then.
>
> _Pivoted 2026-05-07._

---

# Daily Readiness Digest — Standalone Agent Flow (Episode 7, Part 2) — DEFERRED

A **standalone Copilot Studio Agent Flow** that runs every weekday morning at 8 AM. It calls `lc_CalculateLaunchReadiness` for every active launch and posts a single digest to a Microsoft Teams channel.

> **Scope clarification:** this is an **Agent Flow** (Copilot Studio Flows canvas), not a Power Automate cloud flow. The Dataverse MCP step type is a first-class step in Agent Flows. Don't build this in `flow.microsoft.com` — different surface, different ALM story, and it would defeat the Episode 7 narrative ("MCP tools and MCP flow steps are the same primitive").

> **Why standalone (not inside Sentinel):** the flow doesn't use any of Sentinel's instructions, topics, or knowledge — it's pure deterministic orchestration (list → loop → call API → post). Hosting it inside the bot would be narrative theater, not architecture. The Episode 7 framing is "**the autonomous tier has two surfaces**": Sentinel (event-driven, LLM-reasoning) **and** this flow (cron-driven, deterministic). Both call the **same** Dataverse MCP server. That's the punch line.

> **MCP step UX (preview):** newer tenants render the Dataverse MCP step as a **single Instructions box**. **Verified in this tenant:** the box accepts **raw Dataverse SQL** (the same dialect as the MCP `read_query` tool), and that's the most reliable shape — natural-language filters on choice columns silently fail with "An error has occurred." Paste SQL directly. For non-SQL operations (invoking a Custom API, creating a record), use a natural-language instruction since SQL doesn't cover those.

---

## Step 0 — Spike: confirm the Dataverse MCP step is in your Agent Flow canvas

5-minute sanity check. Do this before committing to a recording slot.

1. Copilot Studio → **Flows** (top-level nav, not inside an agent) → **+ New agent flow**.
2. Pick a manual trigger (e.g., "Run a flow from chat" or "When invoked manually") — anything you can click "Test" on.
3. **+ Add an action** → search for `Dataverse MCP` (or `MCP`).
4. **If a Dataverse MCP step appears**:
   - In the Instructions box paste this **SQL** (verified — natural-language filters on choice columns fail):
     ```sql
     SELECT lc_launchid, lc_name, lc_launchstatus
     FROM lc_launch
     WHERE lc_launchstatus = 10600002
     ```
   - **Test** the flow.
   - If it returns rows ✅ → proceed to the build below.
5. **If no step type appears**:
   - Delete the spike flow.
   - **Defer Part 2** of Episode 7 to a future re-cut once the step type is GA in your tenant.
   - **Do not** fall back to a Power Automate cloud flow on camera. It changes the surface, the ALM story, and the narrative — better to ship Part 1 alone than to muddy the message.

---

## The build

### Trigger

- **Recurrence (Schedule)** — every weekday at 8:00 AM in your local TZ.
  - Frequency: Day
  - Days of week: Mon, Tue, Wed, Thu, Fri
  - Time: 08:00

### Step 1 — Dataverse MCP: list active launches

- Step type: **Dataverse MCP**
- Connection: same Dataverse env as the Sentinel bot (same MCP server attached to it as a tool — that's the demo point)
- **Instructions box** (paste verbatim — raw SQL):

  ```sql
  SELECT lc_launchid, lc_name, lc_launchstatus, lc_targetdate
  FROM lc_launch
  WHERE lc_launchstatus IN (10600001, 10600002, 10600003)
  ```

  Status codes: 10600001 Planning, 10600002 InProgress, 10600003 ReadyForLaunch (excludes 10600004 Launched and 10600005 OnHold).

- Output to bind in next steps: the array of launch rows.

### Step 2 — For each active launch: call the readiness Custom API

Wrap a **For each** loop around the array from Step 1. Inside the loop, add a second Dataverse MCP step.

- Step type: **Dataverse MCP**
- **Instructions box** (paste verbatim, with `<launch_guid>` bound to the current loop item's `lc_launchid`):

  ```
  Invoke the unbound Custom API named lc_CalculateLaunchReadiness with input parameter LaunchId set to <launch_guid>. Return the output parameters: Score, Decision, BlockerCount, and AtRiskMilestoneCount.
  ```

- The MCP server resolves "invoke unbound Custom API" to the right tool (`invoke_action` / `execute_action` depending on tenant).
- Outputs to capture per iteration: `Score`, `Decision`, `BlockerCount`, `AtRiskMilestoneCount`.

Why a Custom API instead of raw queries: the readiness algorithm was built once in Episode 5 (`plugins/CalculateLaunchReadiness/`). Reusing it here is what lets the demo say "**three callers, one algorithm**: the Coordinator agent, the Sentinel bot, and this flow."

Why this and not raw queries: the Custom API encapsulates the readiness algorithm (built in Episode 5). Re-implementing it inline in the flow would drift from what the Coordinator (Episode 6) and Sentinel (Episode 7 Part 1) use.

### Step 3 — Compose per-launch markdown block

Inside the for-each loop:

```
### {lc_name}
**Score:** {Score} · **Decision:** {Decision}
**Target:** {lc_targetdate}
**Blocked tasks:** {BlockerCount} · **At-risk milestones:** {AtRiskMilestoneCount}
```

### Step 4 — Compose final digest

After the for-each loop, concatenate all blocks with a header:

```
# Launch Readiness — {today, formatted}

{concatenated per-launch blocks}

— Posted by Launch Sentinel · Source: GeneratedByAutomation
```

The trailing `Source:` / `GeneratedByAutomation:` lines mirror the markers Sentinel writes to `lc_statusupdate` rows — same provenance signature across both surfaces.

### Step 5 — Post to Microsoft Teams

- Step type: **Microsoft Teams** action → "Post message in a chat or channel"
  - (A Teams MCP step is also acceptable if your tenant exposes one. The MCP-vs-connector distinction matters for the **Dataverse** step because that's the platform we're showcasing; Teams is just delivery.)
- Post as: **Flow bot** (clearer attribution than the connection owner)
- Post in: **Channel**, then pick the team and channel (or a group chat for the demo)
- Message: the digest from Step 4 (paste the dynamic content)

---

## Identity & permissions

The flow runs as the **connection owner** of the Dataverse MCP connection, not on-behalf-of the user who authored a row. For the demo, use a clearly-named demo account ("Launch Sentinel Demo" or similar) so the Teams post is attributed cleanly.

This is the same identity caveat as the Sentinel bot's autonomous trigger — call it out once in the episode rather than repeating it for each surface.

---

## Demo recording tips

1. **Pre-trigger one successful run** before recording so a fresh Teams post is visible at the top of the channel.
2. **Open with the architecture beat**: "Sentinel from Part 1 reacts to events. This flow runs on a clock. **Same MCP server** — I'm not even reconnecting it — different trigger type. That's the autonomous tier."
3. **Frame the Dataverse MCP step explicitly**: "Notice this isn't the classic Dataverse connector — it's an **MCP step**, and it takes plain English. The same MCP server I attached as a *tool* to the Sentinel bot is here as a *step* in a flow. **MCP tools and MCP flow steps are the same primitive.**"
4. **Show the Custom API call** (Step 2): "And the readiness algorithm I built in Episode 5? Still doing the work. Same Custom API, three callers now: the Coordinator agent, the Sentinel bot, and this flow."
5. **End on the Teams post** — that's the visual payoff.

---

## What's NOT in this artifact (deferred)

- **Solution-export / ALM packaging.** Standalone Agent Flows can be added to a solution, but the schedule trigger and connections still need to be re-bound in any new env. Don't promise turnkey export.
- **Adaptive Cards in Teams.** Plain markdown body is enough for the demo; Adaptive Cards are a stylistic upgrade with no narrative payoff.
- **Per-launch DMs to launch owners.** Single channel post is the demo. Owner DMs would require a teammember lookup chain — left as an exercise for the audience.
- **Holiday/timezone handling.** Single-TZ schedule for the demo. Productionizing for multiple TZs is out of scope.
- **Power Automate cloud flow as a fallback.** Intentionally excluded — see Step 0. If the MCP step isn't available, defer Part 2 instead of changing surfaces.
