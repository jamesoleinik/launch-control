# Launch Readiness Playbook

**Owner:** Launch Operations  
**Category:** Playbook  
**Audience:** Product directors, launch managers, and engineering leads  
**Last reviewed:** 2026-04-15

This playbook describes the standard procedure that every product launch at our
fictional company follows from kickoff to GA. It is the source of truth used
by the Launch Coordinator agent when answering go/no-go and process questions.

## 1. Phases

A launch passes through five phases. Each phase has explicit entry and exit
criteria. The Launch Coordinator agent enforces them by querying the unified
`lc_Launch` model.

| Phase           | Entry criteria                                | Exit criteria                                |
|-----------------|-----------------------------------------------|----------------------------------------------|
| Planning        | Launch record created, target date set        | Scope locked, milestones in place            |
| In Progress     | All milestones owned, ≥80% tasks scheduled    | All P0 tasks Done, no Blocked tasks          |
| Ready           | All readiness gates green for 5 business days | Go/no-go approved by directors               |
| Launched        | Launch executed                               | 14-day stabilization window cleared          |
| On Hold         | Director sign-off on hold reason              | Re-entry approved by Launch Operations       |

## 2. Readiness gates

The following gates are evaluated by the `lc_CalculateLaunchReadiness` custom
action. A launch is *ready* when **every** gate is green.

1. **Engineering** — zero P0 bugs open, code freeze complies with policy.
2. **Marketing** — campaign plan approved, assets uploaded.
3. **Sales enablement** — playbook published, training delivered.
4. **Support** — runbooks published, on-call rotation set.
5. **Compliance** — privacy review, accessibility, and security reviews complete.
6. **Legal** — final terms reviewed and signed.

Each gate corresponds to a `lc_Milestone` whose status drives the rollup.

## 3. Slipping a launch

A launch may be slipped (target date moved out) under these conditions:

* The slip is **less than one week**: the launch director may approve and must
  log a `lc_StatusUpdate` with reason and new target date.
* The slip is **one to four weeks**: requires the launch director plus the
  product VP. Marketing must re-confirm campaign timing.
* The slip is **more than four weeks**: requires the executive review board.
  The launch is automatically moved to `On Hold` until the board reviews.

In every case the agent must record a status update and notify the launch
Teams channel.

## 4. Roles and responsibilities

* **Launch director** — owns the `lc_Launch` record and the final go/no-go.
* **Engineering lead** — owns engineering readiness gate.
* **Marketing manager** — owns marketing gate and the launch announcement.
* **Sales enablement** — owns the sales gate and field readiness.
* **Support manager** — owns support gate and runbooks.
* **Compliance officer** — owns compliance gate.
* **Legal counsel** — owns legal gate.

## 5. Rituals

* **Weekly launch review** — all gate owners meet, agent posts auto-summary.
* **Daily blocker triage** — Launch Coordinator agent surfaces any task whose
  `lc_IsBlocked` flag has flipped in the last 24 hours.
* **Go/no-go meeting** — three business days before target date.

## 6. Escalation

See `escalation-policy.md` for the full escalation procedure. The short
version: any blocker untouched for 48 hours is auto-escalated to the launch
director, and any critical blocker that prevents a readiness gate from going
green is escalated to the product VP within 24 hours.
