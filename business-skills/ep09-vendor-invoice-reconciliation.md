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
(`PurchFormLetter`); the API-native levers are submitting a pending vendor invoice to an
approval workflow (`SubmitToWorkflow` on the pending-vendor-invoice entity) or a Dataverse
**Custom API** wrapper (the F&O vendor-invoice operations already surface in Dataverse as
`msdyn_VendInvoice*CustomAPI`, which the Dataverse MCP can invoke). We keep all of those
human-gated on purpose. So your authorized output is the drafted follow-up plus, at most,
recording the outstanding vendor invoice as pending for a human to submit and post. A human
owns any ledger posting.

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
- It does **not** post to the ledger, by policy. The F&O ERP MCP (OData) has no post or
  action-invoke tool, and posting is an X++ operation (`PurchFormLetter`); the API-native
  levers (submit-to-workflow, or a Dataverse Custom API wrapper such as the existing
  `msdyn_VendInvoice*CustomAPI`) are kept human-gated on purpose. The agent drafts the
  follow-up and may record a pending invoice at most; a human posts.
- It does **not** answer a human prompt. The runtime is the Dataverse row-add trigger;
  the agent reconciles one signal per event.
- It does **not** double-process. Idempotency on `lc_status` is mandatory across
  retries and re-fires.
