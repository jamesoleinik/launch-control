# Vendor Invoice Reconciliation (event-driven, from a launch procurement signal)

## Description

The Season 2 / Episode 9 Business Skill (Act 3) for the **asynchronous** Launch
Control agent (Act 4). The agent is not prompted by a human; it wakes on a Dataverse event,
"When a row is added -- Microsoft Dataverse" on the `lc_reconciliation` table. Each
new row is a procurement signal a recurring Finance & Operations batch emitted: one
vendor engagement whose committed amount is under-invoiced. This skill defines how
the agent reconciles that single gap across two planes (the launch plan in Dataverse
and the financial truth in Finance & Operations) and writes back exactly one grounded
outcome. It owns the reasoning; the batch only emits the event.

## Instructions

### Step 1: Read the trigger row (Dataverse)

Using the Dataverse MCP, read the `lc_reconciliation` row that fired the trigger.
Take from it: `lc_ponumber`, `lc_vendoraccount` / `lc_vendorname`, `lc_launchcode`,
`lc_committedamount`, `lc_invoicedamount`, `lc_gapamount`, and the `lc_vendorworkid`
lookup to the source engagement. If `lc_status` is anything other than `Open` (it
already reads `Reconciled - Match` or `Reconciled - Gap`), stop: this signal has been
handled (idempotency, see Step 5).

### Step 2: Confirm the gap against Finance & Operations (ERP)

Do not trust the amounts on the signal row blindly; they are a snapshot from when the
batch ran. Using the Dynamics 365 ERP MCP, read the live financial truth for this PO:

- the purchase order header for `lc_ponumber` (vendor, currency, status),
- the invoiced-to-date for that PO (vendor invoice journal / the invoiced amount on
  the order), versus the committed order total.

Recompute the real gap = committed minus invoiced from F&O. If the ERP MCP or the F&O
data is unreachable in this build, you cannot confirm invoiced-to-date: do not treat the
snapshot on the `lc_reconciliation` row as final or fabricate a gap from it. Say so
plainly and hold the signal (see Step 5) rather than closing it.

### Step 3: Decide (POLICY)

- **Gap closed** (F&O now shows fully invoiced / no remaining commitment): no dollars
  are outstanding. Record that the signal is stale and resolved.
- **Gap confirmed and material** (remaining commitment at or above the materiality
  floor, default the signal's `lc_gapamount`): this is a genuine outstanding vendor
  commitment. Draft the follow-up: which vendor to chase, for which PO, for how much,
  tied to which launch task.
- **Gap confirmed but immaterial** (below the floor): note it and close without a
  follow-up action.

The trigger is always the gap relative to the live F&O truth, never the raw number on
the row.

### Step 4: Make the authorized F&O entry and draft the follow-up (grounded)

For a confirmed material gap, produce a short, executive follow-up: the vendor and PO,
the outstanding amount, the launch and task it belongs to, and the single next action
(for example "request invoice from Contoso for PO-10502, 25,000 outstanding, blocks
the Launch video task on WIDGET-Q3"). Using the Dynamics 365 ERP MCP, you may make the
authorized vendor / purchase order / invoice entry the follow-up calls for. You may
**not** post an invoice or journal to the ledger on your own: a human approves any
ledger posting. Ground every entry in its source so a reviewer can trace it.

### Step 5: Write back one outcome and close the signal (idempotent)

Using the Dataverse MCP, update the **same** `lc_reconciliation` row:

- set `lc_agentoutcome` to the grounded summary from Step 3/4 (the verdict, the F&O
  figures used, and the drafted next action or the reason for closing),
- set `lc_status` to the terminal value for the verdict: `Reconciled - Match` when the
  gap is closed (fully invoiced), or `Reconciled - Gap` when a gap is confirmed (whether
  material or immaterial). If F&O was unreachable in Step 2, do **not** mark the row
  reconciled: leave `lc_status` as `Open` and flag it for re-confirmation once F&O is
  back, so the signal is retried rather than falsely closed.

Write exactly once per signal. Before writing, re-check `lc_status`; if another run
already moved it off `Open`, do nothing. Never create a second `lc_reconciliation`
row; the batch owns row creation, the agent only closes rows.

## What this skill is NOT

- It does **not** create `lc_reconciliation` rows. The recurring F&O batch (native
  X++ SysOperation class, or the signal-producer script that stands in for it) is the
  sole producer. The agent is the consumer.
- It does **not** post to the ledger. It may make the authorized vendor / PO / invoice
  entry in Finance & Operations through the ERP MCP, but posting an invoice or journal
  to the ledger is a separate, human-approved action.
- It does **not** answer a human prompt. The runtime is the Dataverse row-add trigger;
  the agent reconciles one signal per event.
- It does **not** double-process. Idempotency on `lc_status` is mandatory across
  retries and re-fires.
