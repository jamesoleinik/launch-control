# Launch ERP Readiness (CRM + ERP all-in verdict)

## Description

The Season 2 / Episode 9 Business Skill for the Launch Control ERP Readiness
agent. The agent reasons across two planes that now live on one platform: the
go-to-market state (Dataverse `lc_` launch tables) and the financial and supply
state (Dynamics 365 Finance & Operations, reached through the ERP MCP). This skill
defines how it combines them into one verdict: GO, AT-RISK, or NO-GO. It never
gives a go-to-market answer without checking ERP, and never gives a financial
answer without checking launch readiness.

## Instructions

### Step 1: Resolve the launch

If the user names a launch (for example "Q3 Widget Launch"), use it. If not, query
`lc_launch` and ask which one. Do not guess and do not silently pick the most
recent. Record the launch SKU or product code, the project or campaign name, and
any vendor named on the launch: these are the join keys to ERP.

### Step 2: Read the go-to-market state (Dataverse)

Using the Dataverse MCP, read from the launch system of record:

- `lc_launch`: the launch, its `lc_launchstatus`, target date, owner.
- `lc_task`: all open and blocked work. Blocked tasks are `lc_taskstatus` =
  Blocked. The task title is `lc_title`.
- `lc_milestone`: milestone health (`lc_milestonestatus`), especially AtRisk and
  Blocked.
- `lc_statusupdate`: the most recent health signal (`lc_health`).

Summarize the internal posture: readiness, the named blockers, their owners and
due dates.

### Step 3: Read the financial and supply state (Finance & Operations)

Using the Dynamics 365 ERP MCP data tools, read the ERP posture for this launch:

- **Budget versus actuals** for the launch project or campaign: is it over the
  approved budget?
- **Open purchase orders** tied to the launch: vendor commitments that are not yet
  received (a launch component still in transit is a supply risk).
- **On-hand inventory** for the launch SKU: is there stock to ship?

Confirm the legal entity before reading, and use the join keys from Step 1. If you
cannot make a confident join, say which ERP record you used and why.

### Step 4: Synthesize one verdict (POLICY)

Combine both planes into a single verdict. Apply this policy:

| Condition | Verdict |
|---|---|
| No open blockers and ERP is on-budget, no open critical PO, inventory available | **GO** |
| Either plane shows a non-critical risk (a slip, a yellow milestone, slightly over budget) | **AT-RISK** |
| Either plane shows a critical blocker (a critical blocked task, over budget AND an open vendor PO, or no inventory) | **NO-GO** |

A launch can be NO-GO from the ERP side alone even when its tasks look fine, and
vice versa. State which plane drove the verdict.

### Step 5: Report

- Lead with the verdict (GO / AT-RISK / NO-GO) in the first sentence.
- Give a two-column read: Go-to-market (Dataverse) and Financial and supply (F&O).
- List the specific blockers on each side, by name.
- Cite the source of every fact (the Dataverse table or the F&O entity) so a
  reviewer can trace it.

## What this skill is NOT

- It is **not** read-then-act. It is read-only by default. Only create or post in
  F&O (a purchase order, a journal) when the user explicitly asks, and confirm the
  legal entity first.
- It does **not** copy ERP data into Dataverse rows. ERP facts are read through the
  ERP MCP at question time; the launch record is not enriched with stored ERP
  columns.
- It does **not** guess when a data source is empty or unreachable. It says so
  plainly.
