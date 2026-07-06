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

**The trigger context can arrive two ways.** Normally you read it from the stored
`lc_reconciliation` row. If instead you are invoked with the trigger context supplied
to you directly (the PO number, committed, and invoiced figures stated in the request,
as in a test or what-if evaluation), treat those supplied figures as the signal
snapshot and continue. Do not refuse merely because a stored row is absent or the
table is empty; the supplied context is the signal. You still ground everything you
can against live F&O in Step 2, and in Step 5 you present the outcome you *would* write
back. Idempotency still applies: if the supplied context (or the stored row) says the
signal already reads `Reconciled - Match` or `Reconciled - Gap`, stop and make no
further changes.

### Step 2: Confirm the commitment against Finance & Operations (ERP)

Using the Dynamics 365 ERP MCP, confirm the purchase order commitment against the live
F&O ledger for this PO.

**Query the `dat` legal entity (company `DAT`), not `USMF`.** Every Launch Control PO,
vendor, and invoice lives in the `dat` company. `USMF` is the F&O demo default and holds
none of this data: querying it returns an empty result at best and an "Internal Server
Error" from the SQL data tool at worst. Always constrain the read to `dataAreaId eq 'dat'`
(or pass the company / `companyId` as `DAT`). If a read errors or comes back empty,
re-check the legal entity is `dat` before concluding F&O is unreachable.

Read the purchase order header from **`PurchaseOrderHeadersV2`** in `dat`, filtered on
`dataAreaId eq 'dat' and PurchaseOrderNumber eq '<lc_ponumber>'`: take
`OrderVendorAccountNumber`, `PurchaseOrderName`, `CurrencyCode`, `PurchaseOrderStatus`,
and `DocumentApprovalStatus`. Use the exact entity and field names above; do not guess
field names. Confirm the PO is a real, approved, open commitment and that its vendor
matches the signal row (flag any vendor mismatch instead of glossing over it).

**Invoiced-to-date.** F&O is the system of record for posted vendor invoices; the launch
procurement signal (`lc_reconciliation` / `lc_vendorwork`) tracks invoicing progress for
the launch. Posted vendor invoices live in **`VendInvoiceJournalHeaders`** (the posted
journal); pending, not-yet-posted invoices live in **`VendorInvoiceHeaders`**. The PO
header (`PurchaseOrderHeadersV2`) has no invoiced-amount field, so do not read
invoiced-to-date off the PO. Read the posted journal for the PO in `dat`:

- If `VendInvoiceJournalHeaders` has posted vendor invoices for the PO, those are
  authoritative: use their total as invoiced-to-date, even if it differs from the signal
  (the ledger wins; note the discrepancy).
- If F&O has no posted invoices for the PO (an empty result, which is the normal state in
  this build until invoices post), take invoiced-to-date from the signal row's
  `lc_invoicedamount`. An empty result is a real "not yet posted in the ledger," not a
  legal-entity error. F&O still confirms the PO commitment; the snapshot supplies
  invoiced-to-date.

Recompute the real gap = committed (confirmed in F&O) minus invoiced-to-date. If the ERP
MCP or the F&O data is genuinely unreachable in this build (after confirming the legal
entity is `dat`), you cannot confirm the commitment: do not fabricate a verdict. Say so
plainly and hold the signal (see Step 5) rather than closing it.

**How the F&O invoice cycle shapes the gap.** In Dynamics 365 F&O a PO-based vendor
invoice completes a three-step cycle: purchase order (the commitment) then product
receipt (goods or services received, in `ProductReceiptHeaders` / `ProductReceiptLines`)
then vendor invoice. A vendor is normally invoiced only for what has been received, so the
committed-minus-invoiced gap has two parts: a **deliver remainder** (ordered but not yet
received) and an **invoice remainder** (received on a product receipt but not yet
invoiced). The portion that genuinely warrants chasing a vendor invoice is the invoice
remainder (received, not invoiced); the not-yet-delivered portion is a delivery matter, not
an invoice matter, so call it out as such rather than dunning for an invoice that is not yet
due. When a posted vendor invoice clears the last remainder, F&O flips
`PurchaseOrderStatus` to `Invoiced`; while any remainder is open it stays `Backorder` (or
`Received`), and more invoices can post against it. In this build no product receipts are
posted yet (`ProductReceiptHeaders` is empty and the POs read `Backorder`), so the full
committed amount is still an open commitment and the signal's `lc_invoicedamount` stands as
invoiced-to-date; note in your outcome that the gap is pre-receipt when that is the case.

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

### Step 4: Draft the grounded follow-up (no ledger posting)

For a confirmed material gap, produce a short, executive follow-up: the vendor and PO,
the outstanding amount, the launch and task it belongs to, and the single next action
(for example "request invoice from Contoso for PO-10502, 25,000 outstanding, blocks
the Launch video task on WIDGET-Q3"). Ground every figure in its source so a reviewer
can trace it.

You may **not** post a vendor invoice or journal to the ledger. This is a deliberate
policy choice, and the platform makes it the path of least resistance. The **F&O ERP MCP**
(OData) exposes no post or action-invoke tool at all: it is record CRUD, so the agent
cannot post through it. Posting a PO-matched vendor invoice is an X++ ledger operation
(`PurchFormLetter`) that runs inside F&O only after a human approves the vendor-invoice
workflow; there is no direct "post to ledger" API. The F&O vendor-invoice operations do
surface in Dataverse as invokable **Custom APIs** (`msdyn_VendInvoice*CustomAPI`), but the
only one that advances an invoice is `msdyn_VendInvoiceSubmitToWorkflowCustomAPI`
(`invoiceId`, `comment`): it submits a pending invoice to the approval workflow, it does
not post. No `msdyn_VendInvoice*PostCustomAPI` exists. The actual ledger post is observed
after the fact through the `mserp_VendorInvoiceJournalPostedBusinessEvent`. We keep the
submit-to-workflow lever human-gated on purpose. So your authorized output is the drafted
follow-up plus, at most, recording the outstanding vendor invoice as pending for a human to
submit and post. A human owns any ledger posting.

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

If you were invoked with supplied trigger context and there is no stored row to update
(a test or what-if evaluation), do not treat that as a blocker: state the exact
`lc_agentoutcome` and `lc_status` you *would* write, grounded the same way. Presenting
the outcome you would write back is a valid completion; refusing solely because there
is no row to persist to is not.

## What this skill is NOT

- It does **not** create `lc_reconciliation` rows. The recurring F&O batch (native
  X++ SysOperation class, or the signal-producer script that stands in for it) is the
  sole producer. The agent is the consumer.
- It does **not** post to the ledger, by policy. The F&O ERP MCP (OData) has no post or
  action-invoke tool, and posting is an X++ operation (`PurchFormLetter`) that F&O runs only
  after a human approves the workflow. The one API-native lever that surfaces in Dataverse,
  `msdyn_VendInvoiceSubmitToWorkflowCustomAPI`, only submits a pending invoice for approval
  (there is no direct-post Custom API); it is kept human-gated on purpose. The agent drafts
  the follow-up and may record a pending invoice at most; a human posts.
- It does **not** answer a human prompt. The runtime is the Dataverse row-add trigger;
  the agent reconciles one signal per event.
- It does **not** double-process. Idempotency on `lc_status` is mandatory across
  retries and re-fires.
