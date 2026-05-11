# Escalation Policy

**Owner:** Launch Operations  
**Category:** Policy  
**Last reviewed:** 2026-04-12

This policy defines how blockers and risks on a product launch are escalated.
The Launch Coordinator agent uses it as both a reference document and a
runtime rulebook for the `lc_EscalateBlocker` skill.

## 1. Severities

* **S1 — Critical.** Blocks a readiness gate from going green; or a customer-
  facing incident that requires the launch to slip.
* **S2 — High.** Slows a milestone but does not block a gate.
* **S3 — Normal.** Routine issue that the assignee should resolve in their
  next working day.

The agent infers severity from the `lc_Task.lc_BlockerReason` field plus the
gate impact on the parent `lc_Milestone`.

## 2. Time-based triggers

| Trigger                                       | Action                                  |
|-----------------------------------------------|-----------------------------------------|
| `lc_IsBlocked = true` for 24 hours            | Notify the assignee and milestone owner |
| `lc_IsBlocked = true` for 48 hours            | Escalate to the launch director         |
| S1 issue not acknowledged within 4 hours      | Escalate to the product VP              |
| Readiness gate red within 5 days of target    | Auto-trigger go/no-go review            |

The agent emits a `lc_StatusUpdate` for every escalation.

## 3. Channels

* **First-line communications** happen in the launch Teams channel. The
  agent posts a card with the blocker and links to the `lc_Task` record.
* **Director escalation** uses email plus a Teams direct message.
* **VP escalation** uses email and is announced in the weekly launch review.

## 4. Quiet hours

The agent honors organizational quiet hours (local 22:00–07:00) for all
non-S1 escalations. S1 escalations are sent immediately regardless of time.

## 5. Acknowledgement

Every escalation expects an acknowledgement. The agent tracks acknowledgement
via reactions in Teams or a status update on the `lc_Task` record. If no
acknowledgement is recorded within the time-based trigger window, the next
level of escalation fires automatically.

## 6. Override

The launch director may override any rule in this policy by recording a
`lc_StatusUpdate` with the body prefix `OVERRIDE:` and a justification. The
override is logged but not auto-reversed.
