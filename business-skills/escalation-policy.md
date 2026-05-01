# Escalation Policy

## Description
Follow this policy when a launch task or milestone is blocked. Determines
severity, notification chain, and resolution timeline. Always check whether
a blocked task has a linked GitHub issue (via the `lc_GitHubIssueId` virtual
entity lookup) before deciding severity — an open GitHub issue with
"blocker" or "P0" labels has independent signal that affects severity.

## Instructions

When a task or milestone is blocked, follow this escalation policy to
resolve the blocker.

### Step 0: Verify the block is real (cross-system check)

Before escalating, verify that the task is actually blocked in every
system that knows about it. If the task has a linked GitHub issue, the
`lc_state` from the virtual entity is the source of truth for engineering
work — never trust the Dataverse `lc_taskstatus` alone for engineering
tasks.

```
GET /api/data/v9.2/lc_tasks(<id>)
   ?$select=lc_title,lc_taskstatus,lc_isblocked,lc_blockerreason,_lc_githubissueid_value
   &$expand=lc_GitHubIssueId($select=lc_issuenumber,lc_state,lc_labels,lc_url)
```

Rules:

- If `lc_taskstatus = Blocked (10600023)` AND `lc_GitHubIssueId.lc_state =
  closed`: the GitHub issue is resolved but Dataverse is stale. **Do not
  escalate.** Recommend transitioning the task back to In Progress (use
  the Status Transition Rules skill) and run readiness again.
- If `lc_taskstatus = Blocked` AND `lc_GitHubIssueId.lc_state = open` AND
  the issue's `lc_labels` contain `blocker` or `P0`: severity is at least
  **High**, possibly **Critical**. The GitHub label is a stronger signal
  than the Dataverse blocker text alone.
- If the task has no GitHub link, proceed with severity assessment based
  on Dataverse fields only (`lc_isblocked`, `lc_blockerreason`,
  `lc_duedate`).

### Step 1: Assess severity

Use the milestone's `lc_duedate` (NOT the launch's `lc_targetdate` — the
milestone is the immediate deadline) to determine days remaining.

| Severity | Trigger |
|---|---|
| **Low**      | Task blocked, milestone due > 5 days away, only one task affected |
| **Medium**   | Task blocked, milestone due 2–5 days away, OR 2+ tasks blocked in same milestone |
| **High**     | Task blocked, milestone due < 2 days away, OR a critical-path task blocked, OR linked GitHub issue labelled `blocker`/`P0` |
| **Critical** | Any of: launch date at risk, multiple milestones blocked, sponsor sign-off pending, OR `lc_CalculateLaunchReadiness` returns NO-GO |

If in doubt, invoke `lc_CalculateLaunchReadiness` for the parent launch.
A NO-GO verdict is independent evidence that severity should be at least
High.

### Step 2: Notify

Resolve recipients by walking the lookups (no separate sponsor field exists
on `lc_launch` today — use the assigned team members and the launch's
program manager known to the agent context):

- Task assignee: expand `_lc_assignedtoid_value` on the task to read
  `lc_teammember.lc_email` and `lc_teammember.lc_role`.
- Milestone owner: expand `_lc_assignedtoid_value` on the milestone the
  same way.
- Program manager / sponsor: provided via the agent's environment context
  (e.g., a Copilot Studio variable or skill input) — do NOT hard-code an
  email address into the skill output.

Notification chain by severity:

| Severity | Notify |
|---|---|
| Low      | Task assignee. Reminder + ETA request. |
| Medium   | Task assignee + milestone owner. Request resolution plan within 24h. |
| High     | Task assignee + milestone owner + program manager. Schedule 15-min sync within 4h. |
| Critical | All of the above + launch sponsor. Emergency sync within 1h. |

When a linked GitHub issue exists, include `lc_url` in the notification so
recipients can comment directly on the issue. Do not duplicate notifications
on GitHub — leave that to the engineering on-call rotation.

### Step 3: Record the escalation

Write a status-update row on the launch capturing the escalation. The
canonical table for narrative state changes is `lc_statusupdate` (one
record per launch update; linked to the launch via `lc_LaunchId`):

```http
POST /api/data/v9.2/lc_statusupdates
Content-Type: application/json

{
  "lc_name":           "[<Severity>] <task or milestone title> blocked",
  "lc_LaunchId@odata.bind": "/lc_launchs(<launchid>)"
}
```

The `lc_name` is the operator-readable summary the agent should compose
in this format, so the launch's status-update timeline reads cleanly:

```
[High] Wire payment provider blocked — GitHub #4 open, P0; ETA 2026-05-04
```

If your environment extends `lc_statusupdate` with additional fields
(severity choice, notified-parties memo, ETA datetime, GitHub URL, status
choice), populate them. The skill must not assume those fields exist —
operate on `lc_name` + `lc_LaunchId` as the guaranteed minimum.

### Step 4: Track resolution against SLA

| Severity | SLA before auto-re-escalate |
|---|---|
| Low      | 3 days   |
| Medium   | 24 hours |
| High     | 4 hours  |
| Critical | 1 hour   |

If the underlying task is still `lc_isblocked = true` after the SLA
window, raise severity by one level and re-run Step 2. Write a fresh
`lc_statusupdate` row each time so the timeline preserves history.

For escalations linked to a GitHub issue, also re-check `lc_state` on the
virtual entity at SLA boundaries — if the issue closes between checks,
auto-resolve the escalation: write a `[Resolved] …` `lc_statusupdate` row
referencing the original blocker text and the GitHub close timestamp.

### Step 5: Post-resolution

When the blocker clears:

1. **Update the task status.** Use the Status Transition Rules skill —
   `Blocked → In Progress` or `Blocked → Done` depending on whether work
   remains. That skill also clears `lc_isblocked` and runs the
   cross-system check if the task is GitHub-linked.
2. **Write a `[Resolved]` status update.** Same `lc_statusupdate` table,
   linked to the launch, with a short post-mortem in `lc_name`.
3. **Recompute launch readiness.** Invoke `lc_CalculateLaunchReadiness`
   on the parent launch — the verdict may now be CONDITIONAL or GO.
4. **If the milestone date slipped**, surface that to the program manager
   with a recommendation to update `lc_milestone.lc_duedate`.

### What this skill is NOT

- It is **not** a way to set status. State changes go through the Status
  Transition Rules skill, which has its own validation logic.
- It does **not** compute readiness. That's `lc_CalculateLaunchReadiness`
  (Launch Readiness Checklist skill). This skill _consumes_ that verdict
  as one input to severity.
- It does **not** modify GitHub. The virtual entity is read-only and the
  GitHub issue's lifecycle is owned by engineering.
