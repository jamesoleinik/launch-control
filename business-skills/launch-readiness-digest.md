# Launch Readiness Digest

## Description

Compose and post a daily readiness digest summarizing the state of every
active launch. Used by the **Launch Sentinel** autonomous agent (Ep 9)
when its recurrence trigger fires (Mon–Fri 08:00). Same agent that handles
event-driven escalation (Escalation Policy skill, autonomous mode), but a
fundamentally different job: read-only across the entire active portfolio,
score each launch via the readiness Custom API, and post a single
markdown summary to a notification channel.

This skill is the canonical home for digest format, scope, and
partial-failure handling. The Sentinel prompt should load this skill
first and follow it; the inline template in the prompt is a fallback
only.

## Instructions

### Trigger discriminator

The Sentinel agent has two triggers attached:

- **Event** trigger on `lc_task` (payload contains `lc_taskid`) → run the
  Escalation Policy skill, autonomous mode.
- **Recurrence** trigger Mon–Fri 08:00 (payload empty / timestamp-only)
  → run **this** skill.

If the payload contains `lc_taskid`, this is the wrong skill. Exit and
let the Escalation Policy skill take over.

### Step 1 — List active launches via Dataverse MCP `read_query`

Run EXACTLY this SQL — no other queries during the digest:

```sql
SELECT lc_launchid, lc_name, lc_launchstatus, lc_targetdate
FROM lc_launch
WHERE lc_launchstatus IN (10600001, 10600002, 10600003)
```

The three IN values are: 10600001 Planning, 10600002 InProgress, 10600003
ReadyForLaunch. Never include 10600004 Launched or 10600005 OnHold —
those launches don't need a daily readiness check.

**Dataverse SQL naming caveat:** the `read_query` MCP tool uses
Dataverse SQL where lookup columns are `lc_milestoneid` (no leading
underscore, no `_value` suffix). The OData-style `_lc_milestoneid_value`
form is for Web API GETs (the kind of query the Escalation Policy skill
uses), never in `read_query` SQL.

Do NOT query `lc_task`, `lc_milestone`, or `lc_statusupdate` here —
Step 2's Custom API already aggregates blocker and at-risk-milestone
counts. Extra queries cause off-script errors and slow the digest.

If zero rows are returned → post a single line:

```
Launch Readiness — <today>: no active launches.
```

…and exit.

### Step 2 — Score each launch via Custom API

For each row from Step 1, invoke the Dataverse MCP unbound action
`lc_CalculateLaunchReadiness` with input `LaunchId = <lc_launchid>`.
Capture from the response:

- `Score` (integer, 0–100)
- `Decision` (`GO` | `CONDITIONAL` | `NO-GO`)
- `BlockerCount` (integer)
- `AtRiskMilestoneCount` (integer)

**Partial-failure handling.** If the action errors for one launch (404,
plugin exception, timeout) do NOT abort the whole digest. Substitute:

- `Score = ?`
- `Decision = ERROR`
- `BlockerCount = ?`
- `AtRiskMilestoneCount = ?`

…and continue with the remaining launches. The reader needs to see that
the launch was checked, even if scoring failed. Silent omission is the
worst outcome.

### Step 3 — Compose the markdown digest

Use this exact template:

```
# Launch Readiness — <today, "Mon Jan 02 2026">

## <lc_name>
**Decision:** <Decision> · **Score:** <Score>/100
**Target:** <lc_targetdate, "2026-01-02">
**Blocked tasks:** <BlockerCount> · **At-risk milestones:** <AtRiskMilestoneCount>

(...repeat per launch...)

— Posted by Launch Sentinel · GeneratedByAutomation: true
```

The `GeneratedByAutomation: true` footer is the same provenance marker
the Escalation Policy skill writes into `lc_statusupdate.lc_body` —
same agent, same signature. Audit queries and downstream consumers can
recognize Sentinel-authored content from either surface.

Format rules:

- Date format: `Mon Jan 02 2026` (locale-stable, no ambiguity).
- Order launches by `lc_targetdate` ascending (closest to launch first).
- One H2 (`##`) per launch. Do not nest deeper.
- Never include `lc_launchid` GUIDs in the digest body — they're not
  reader-friendly. The launch name is the human handle.

### Step 4 — Post to the notification channel

Call the Teams MCP tool action `SendMessageToSelf` with:

- `content` = the markdown from Step 3
- `contentType = html` (Notes to Self renders markdown like any Teams
  chat)

**Single-tool rule.** Only `SendMessageToSelf` is enabled on the Teams
MCP for this agent. Never call `SendMessageToUser`,
`SendMessageToChat`, or `SendMessageToChannel`. The digest goes to the
agent's own Notes to Self chat — fan-out to other recipients is a
separate, future concern.

If the Teams call fails → exit silently. No retries, no Dataverse
fallback row. Tomorrow's run will cover any missed slot. The digest is
a convenience surface; missing one day is not an incident.

### Guardrails

1. **One digest per recurrence invocation.** Never post twice for the
   same trigger fire.
2. **Read-only on Dataverse.** The digest never writes any row — not
   `lc_statusupdate`, not anything. Writes are owned by the Escalation
   Policy skill (autonomous mode).
3. **Only the locked SQL in Step 1.** No exploratory queries, no
   per-launch task drill-downs. The Custom API is the aggregation
   contract.
4. **Only `SendMessageToSelf` on the Teams MCP.** See Step 4.
5. **Partial failure ≠ total failure.** One launch erroring does not
   suppress the rest of the digest.

### What this skill is NOT

- It is **not** an escalation. The digest summarizes; it does not
  notify owners of blocked tasks. That's the Escalation Policy skill
  (autonomous mode), which fires on its own event trigger.
- It is **not** a status update. It does not write to
  `lc_statusupdate` — the launch's status timeline is owned by the
  Coordinator agent and the Escalation Policy skill.
- It is **not** a chat surface. The agent does not answer follow-up
  questions about the digest. Readers who want detail should ask the
  Launch Coordinator agent (Ep 8), which can ground in the same
  Dataverse data interactively.
- It does **not** compute readiness itself — it consumes the Custom
  API's verdict. If the scoring logic needs to change, edit the
  `lc_CalculateLaunchReadiness` plugin (Ep 5), not this skill.
