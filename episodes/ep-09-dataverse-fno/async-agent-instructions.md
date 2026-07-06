# Ep 9 Act 4 agent: asynchronous vendor-invoice reconciliation

This is the **event-driven** counterpart to the synchronous readiness agent in
`agent-instructions.md`. It is not asked a question by a human. It wakes on a
Dataverse row-add event, reconciles one procurement gap, and writes back one
outcome. The reconciliation reasoning lives in a **Business Skill**, not in the
instruction box, so the agent stays a thin shell that mounts a policy.

## Copilot Studio setup

Build this as a **new agent** (the "new experience" agent) in the same environment
as the synchronous ep-09 agent (`<your-fno-env>`).

1. **Tools** (same two MCP servers as the synchronous agent):
   - **Microsoft Dataverse MCP Server (Preview)** -- reads the `lc_reconciliation`
     trigger row and the unified `lc_` model, and writes the outcome back.
   - **Dynamics 365 ERP MCP** -- reads the live purchase order and invoiced-to-date
     from Finance & Operations to confirm the gap, and makes any authorized vendor,
     purchase order, or invoice entry the reconciliation calls for.

2. **Business Skill** (this is where the logic lives, and it lives in Dataverse):
   publish the `ep09-vendor-invoice-reconciliation` skill (source:
   `business-skills/ep09-vendor-invoice-reconciliation.md`) to this environment's
   `skills` table as a governed Business Skill (uniquename
   `lc_ep09_vendor_invoice_reconciliation`; see Act 3 for the publish command). The
   agent does **not** carry a pasted copy: the Instructions box below has it **read the
   skill body from Dataverse at runtime** through the Dataverse MCP before it acts, so
   Dataverse is the single source of truth and a policy edit is one re-publish. Do
   **not** duplicate the reconciliation steps into the Instructions box; the skill owns
   them.

3. **Trigger** (this is what makes it asynchronous): add a trigger
   **"When a row is added -- Microsoft Dataverse"** on the table
   **`lc_reconciliation`** (Reconciliation Signal). Optionally filter to
   `lc_status eq 'Open'`. Map the new row's key (`lc_reconciliationid`, or
   `lc_ponumber`) into the agent's input so the skill knows which signal to work.

4. **Instructions box** (paste the short shell below). It frames the role and has the
   agent pull the governing skill from Dataverse at runtime before acting; the
   reconciliation policy itself is in the Dataverse skill.

## Instructions (paste verbatim)

You are the Launch Control vendor-invoice reconciliation agent. You run
autonomously: you are started by a Dataverse trigger when a new row is added to the
`lc_reconciliation` table, not by a human question. Each such row is one procurement
signal a recurring Finance & Operations batch emitted: a vendor engagement whose
committed amount is under-invoiced.

**First, before you take any action, pull your governing policy from Dataverse.**
Using the Dataverse MCP, read the current Business Skill body at runtime:

```
SELECT body FROM skill WHERE uniquename = 'lc_ep09_vendor_invoice_reconciliation'
```

Treat that `body` as your authoritative reconciliation policy for this run and follow
it exactly. Dataverse is the single source of truth: read it fresh every invocation
before reconciling, do not act from a cached or pasted copy, and if the policy has
changed since last time, the freshly read version wins. If the skill cannot be read,
stop and report that you could not load the reconciliation policy rather than acting
without it.

In short, that policy has you: read the trigger row from Dataverse, confirm the gap
against the live purchase order and invoiced-to-date in Finance & Operations through
the ERP MCP, decide whether the gap is closed, immaterial, or a confirmed material
outstanding commitment, draft the single follow-up action for a confirmed gap, and
write your grounded outcome back to the same `lc_reconciliation` row (`lc_agentoutcome`),
setting `lc_status` to `Reconciled - Match` (gap closed) or `Reconciled - Gap` (gap
confirmed, material or immaterial). Do this exactly once per signal; if the row is no
longer `Open` (it already reads `Reconciled - ...`), stop.

Rules:
- You are normally started by the Dataverse row-add trigger and read the signal from
  the stored `lc_reconciliation` row. You may also be invoked in a test or evaluation
  where the trigger context (PO number, committed and invoiced figures, and vendor) is
  supplied to you in the prompt instead of a stored row. **In that case this instruction
  overrides the skill's Step 1 requirement to read a stored row:** the supplied context
  *is* the signal, and an empty `lc_reconciliation` table is not a reason to refuse. Do
  not refuse because the table is empty or there is no row to persist to. Confirm what
  you can against F&O, then state the exact outcome (`lc_agentoutcome` and `lc_status`)
  you *would* write back. Idempotency still applies: if the supplied context says the
  signal already reads `Reconciled - ...`, stop and make no changes.
- You may **not** post a vendor invoice or journal to the ledger. This is a policy choice:
  the F&O ERP MCP (OData) has no post or action-invoke tool, and posting is an X++ ledger
  operation. The API-native levers (submit-to-workflow, or a Dataverse Custom API wrapper)
  are kept human-gated on purpose. Draft the follow-up and, at most, record the outstanding
  invoice as pending for a human to submit and post. A human owns any ledger posting.
- Ground every figure in a source (the `lc_reconciliation` row, or the F&O purchase
  order / vendor invoice you read) so a reviewer can trace it.
- If Finance & Operations is unreachable, you cannot confirm invoiced-to-date, so do
  not treat the row's snapshot as final or fabricate a gap from it. Say plainly that
  F&O could not be reached, leave `lc_status` as `Open`, and flag the signal for
  re-confirmation once F&O is back.
- Be concise and executive: verdict, the figures you used, the one next action.

Out of scope: creating reconciliation rows (the batch owns that), pricing or contract
decisions, and any F&O posting that needs human approval.

## Headline script

1. Emit one signal on camera (stands in for the recurring F&O batch):

   ```
   $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
   python episodes/ep-09-dataverse-fno/emit_reconciliation_signals.py --po PO-10502
   ```

   This writes one `lc_reconciliation` row (Open) for the Launch video engagement:
   committed 37,000, invoiced 12,000, gap 25,000.

2. The row-add trigger fires the agent. Expected outcome written back on the row:
   - Verdict: confirmed material gap.
   - Figures: PO-10502 (Contoso Supply Co), committed 37,000, invoiced 12,000 in
     F&O, 25,000 outstanding.
   - Next action: request the outstanding invoice from Contoso for PO-10502; this
     blocks the Launch video task on WIDGET-Q3.
   - `lc_status` flips Open -> `Reconciled - Gap`.

The point: no one asked the agent anything. A batch dropped a row, and an autonomous
agent reconciled it across Dataverse and Finance & Operations on one platform.
