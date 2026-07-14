# Vendor Invoice Reconciliation (assistive, from a vendor invoice a person uploads)

## Description

The Season 2 / Episode 9 Business Skill for the **assistive** Launch Control agent. A
person opens a chat, provides a vendor invoice (uploaded or pasted), and says it arrived, for example *"Here
is the latest invoice from Fabrikam Media for the Q3 Widget Launch hero copy work.
Reconcile it before I pay it."* The agent reads the provided invoice, reconciles it
across two planes, records the work as complete when the person confirms delivery, and,
on an explicit go-ahead, posts the vendor invoice, all in the one conversation.

1. **Does the invoice match the purchase order?** The financial truth lives in Dynamics
   365 Finance & Operations. The agent confirms the invoice amount against the PO line
   (amount, matching policy) through the Dynamics 365 ERP MCP.
2. **Is the work actually done?** The project truth lives in Dataverse. The agent
   follows the launch procurement join (`lc_vendorwork -> lc_task`) and reads the
   launch task status through the Dataverse MCP. A task flagged **Blocked** is a
   recorded impediment the agent will not post past. A task still **in flight**
   (`NotStarted` / `InProgress`) is one the person, who owns the work, can confirm is
   delivered; the agent then **records that completion** on the task in Dataverse before
   posting.

When the money and the work agree and the person says go, the agent posts in Finance &
Operations through the ERP MCP **form tools**: it posts the **product receipt** against
the confirmed PO, then posts the **vendor invoice** (see `ep09-vendor-invoice-posting`).
If the amount does not match, the agent **stops and asks for a corrected or new vendor
invoice** rather than posting. If the work is blocked, the agent holds and asks the
person how they want to proceed with the work blocker. A human is always in the loop;
the agent never posts, and never marks work complete, on its own.

This replaces the earlier event-driven design (a recurring batch dropped a signal row
and an autonomous agent chased a committed-vs-invoiced gap). There is no batch, no
trigger, and no `lc_reconciliation` row: the uploaded invoice is the trigger and the
posted F&O vendor invoice is the outcome.

## Data model and how to search it

The reconciliation joins two planes. The **project truth** (is the work done?) lives in
Dataverse; the **financial truth** (does the money match?) lives in Dynamics 365 Finance
& Operations. One Dataverse row, `lc_vendorwork`, is the bridge: it holds the F&O
business keys (vendor account, PO number) and a lookup to the launch task.

**Join path**

```
lc_launch (launch)
   |  lc_launchcode
lc_vendorwork (launch <-> procurement bridge)  --lc_taskid-->  lc_task (the outsourced work)
   |  lc_vendoraccount / lc_ponumber (F&O business keys)
   |  lc_VendorRef / lc_PORef (lookups to the F&O virtual tables)
   v
Dynamics 365 F&O:  VendVendorV2  /  PurchaseOrderHeadersV2  /  PurchaseOrderLinesV2
```

**Dataverse tables (read via the Dataverse MCP)**

- **`lc_vendorwork`** (entity set `lc_vendorworks`): one row per outsourced engagement.
  - `lc_name` (primary name), `lc_workkey` (stable key), `lc_launchcode` (which launch),
    `lc_tasktitle` (matches `lc_task.lc_title`), `lc_scope` (memo).
  - F&O business keys: `lc_vendoraccount`, `lc_vendorname`, `lc_ponumber`.
  - Amounts: `lc_committedamount`, `lc_invoicedamount` (decimals). `lc_status`, `lc_duedate`.
  - Lookups: `lc_taskid` -> `lc_task`; `lc_VendorRef` -> `mserp_vendvendorv2entity`;
    `lc_PORef` -> `mserp_purchpurchaseorderheaderv2entity` (where generated).
- **`lc_task`** (entity set `lc_tasks`): the launch task the engagement outsources.
  - `lc_taskid` (id), `lc_title` (name), and the choice `lc_taskstatus`:
    `NotStarted` = `10600301`, `InProgress` = `10600302`, `Blocked` = `10600303`,
    `Done` = `10600304`.
- **`lc_launch`**: launch context, keyed by `lc_launchcode` (read only if you need the
  launch name for the summary).

**F&O entities (read via the Dynamics 365 ERP MCP OData / data tools)**

- **`PurchaseOrderLinesV2`**: `dataAreaId`, `PurchaseOrderNumber`, `LineAmount`,
  `PurchasePrice`, `OrderedPurchaseQuantity`, `PurchaseOrderLineStatus`,
  `VendorInvoiceMatchingPolicy`. This is the line the invoice amount is matched against.
- **`PurchaseOrderHeadersV2`**: `dataAreaId`, `PurchaseOrderNumber`,
  `OrderVendorAccountNumber`, `PurchaseOrderStatus` (the confirmed PO flips to
  `Invoiced` after a successful post).
- **`VendVendorV2`**: `dataAreaId`, `VendorAccountNumber`, `VendorName` (to confirm the
  vendor account behind the invoice).

### Search strategy (Dataverse first, F&O for the financial truth)

1. **Find the engagement in Dataverse.** Prefer the most specific key the invoice gives
   you. If the invoice cites a PO number, filter `lc_vendorwork` on
   `lc_ponumber eq '<po>'`. Otherwise filter on the launch and vendor, for example
   `lc_launchcode eq '<launchcode>' and lc_vendoraccount eq '<vendoraccount>'`, or match
   `lc_vendorname` against the vendor on the invoice. Read back `lc_ponumber`,
   `lc_vendoraccount`, `lc_committedamount`, `lc_invoicedamount`, and the `lc_taskid`
   lookup. If more than one row matches, list them and ask which invoice this is; do not
   pick one silently.
2. **Read the task status in Dataverse.** Resolve `lc_taskid` to `lc_task` and read
   `lc_taskstatus`. If you only have `lc_tasktitle`, match it to `lc_task.lc_title`.
3. **Confirm the money in F&O.** Take `lc_ponumber` from the engagement and read
   `PurchaseOrderLinesV2` filtered on
   `dataAreaId eq 'dat' and PurchaseOrderNumber eq '<lc_ponumber>'`. Match the invoice
   amount to `LineAmount`. **Always constrain to `dataAreaId eq 'dat'`** (see Step 3).

**Fallback to F&O when Dataverse is thin or the keys disagree.** The invoice, not
Dataverse, is the source of the PO number. So:

- If **no `lc_vendorwork` row matches**, but the invoice cites a PO number, go straight
  to F&O and confirm the PO exists: read `PurchaseOrderHeadersV2` on
  `dataAreaId eq 'dat' and PurchaseOrderNumber eq '<po>'` and its line in
  `PurchaseOrderLinesV2`. Report that the launch has no recorded engagement for this PO
  and ask the person whether to proceed on the F&O record alone; do not invent a
  Dataverse row.
- If the **engagement's `lc_ponumber` and the invoice's PO number disagree**, trust the
  invoice for the financial read (query F&O on the invoice's PO), and flag the mismatch
  to the person.
- If a **Dataverse read fails**, you can still do the financial check from the invoice's
  PO number against F&O, but you cannot complete the work-complete check without
  `lc_task`; say which plane is unavailable rather than guessing.
- If an **F&O read errors or returns empty**, re-check the legal entity is `dat` before
  concluding F&O is unreachable (Step 3). Only after that, hold and say the financial
  truth cannot be confirmed.

## Instructions

### Step 1: Read the invoice the person provides

The person provides the vendor invoice, either by **uploading** it (a PDF or image) or by
**pasting its details** into the chat. Read whichever was provided and take the
**vendor**, the **project / launch** it is for, the **invoice amount**, the
**purchase order number** if the invoice cites one, and the **invoice number** and
**currency**. If the person provides neither an upload nor pasted invoice details, ask
them to supply the invoice before you touch any data; do not reconcile from a remembered
or assumed figure. If a field is missing or
unreadable on the invoice, ask one short clarifying question. Do not guess the vendor,
the launch, or the amount.

### Step 2: Identify the engagement (Dataverse)

Using the Dataverse MCP, find the one `lc_vendorwork` engagement that matches the
vendor and the launch from the invoice. Read `lc_ponumber`, `lc_vendoraccount` /
`lc_vendorname`, `lc_launchcode`, `lc_committedamount`, `lc_invoicedamount`, and the
`lc_taskid` lookup to the outsourced `lc_task`. The engagement carries the F&O business
keys (and, where generated, the `lc_VendorRef` / `lc_PORef` lookups to the F&O virtual
tables) that tie the launch task to the real purchase order. If more than one engagement
matches, list them and ask which invoice this is.

### Step 3: Financial check (Finance & Operations)

Using the Dynamics 365 ERP MCP, confirm the invoice amount against the live purchase
order line.

**Query the `dat` legal entity (company `DAT`), not `USMF`.** Every Launch Control PO,
vendor, and invoice lives in `dat`; `USMF` is the F&O demo default and holds none of
this data. Constrain every read to `dataAreaId eq 'dat'`. If a read errors or comes
back empty, re-check the legal entity is `dat` before concluding F&O is unreachable.

Read the PO line from **`PurchaseOrderLinesV2`**, filtered on
`dataAreaId eq 'dat' and PurchaseOrderNumber eq '<lc_ponumber>'`: take `LineAmount`,
`PurchasePrice`, `OrderedPurchaseQuantity`, `PurchaseOrderLineStatus`, and
`VendorInvoiceMatchingPolicy`. Confirm the invoice amount from Step 1 matches the PO
line amount (`LineAmount`).

- **Amount matches**: the financial side is clean; continue to Step 4.
- **Amount does not match**: stop. State both figures (invoiced vs PO line) and ask the
  person to obtain a corrected or new invoice from the vendor. This is the primary
  blocker: do not post, do not override, and do not partial-pay an invoice that does
  not match the PO line. If the linked Dataverse task is also not `Done`, additionally
  note that work is not yet complete, but keep the recourse focused on a corrected
  invoice.

The PO is already confirmed (`PurchaseOrderStatus` = `Confirmed`); the product receipt
is posted in Step 6 as part of the confirmed post, so the received quantity the
`ThreeWayMatch` needs is created there, not assumed here.

If the ERP MCP or the F&O data is genuinely unreachable (after confirming the legal
entity is `dat`), you cannot confirm the amount: say so plainly and hold. Do not
fabricate a match or post on an unconfirmed figure.

### Step 4: Work-complete check (Dataverse), and record completion when the person confirms

Using the Dataverse MCP, read the outsourced `lc_task` (via the `lc_taskid` lookup from
Step 2) and check `lc_taskstatus`. The status values are `NotStarted` (`10600301`),
`InProgress` (`10600302`), `Blocked` (`10600303`), and `Done` (`10600304`). Branch on
it:

- **Blocked (`10600303`)**: stop. A blocked task is a recorded impediment, and you do
  **not** mark it complete or post past it on a verbal say-so. Tell the person the
  invoice arrived but the launch task is Blocked (name the task), and ask how they want
  to proceed: hold the invoice until the work lands, follow up with the vendor or the
  task owner, or explicitly override. This is the case where Dataverse protects the
  ledger.
- **Done (`10600304`)**: the task already records the work as delivered; continue to
  Step 5.
- **In flight (`NotStarted` or `InProgress`)**: the work is not yet recorded complete.
  Tell the person the task is not marked complete and ask them to confirm the work was
  actually delivered. Only on their explicit confirmation, **record the completion**:
  using the Dataverse MCP, set the `lc_task` `lc_taskstatus` to `Done` (`10600304`), and
  note in your summary that you marked it complete on the person's confirmation. If they
  do not confirm delivery, do not mark it complete and do not post; hold and ask.

Never set a task to `Done` without the person's explicit confirmation that the work was
delivered, and never override a `Blocked` task this way.

### Step 5: Reconcile and decide

- **Both checks pass** (amount matches the PO line, and the task is `Done`, either
  already or because you just recorded it on the person's confirmation): summarize the
  reconciliation in one short, grounded paragraph, the vendor, the PO, the amount, the
  launch and task, each figure tied to its source, and note if you marked the task
  complete. Then **ask the person to confirm the post**: *"Both checks pass. Do you want
  me to post the product receipt and vendor invoice in Finance & Operations?"* Do not
  post yet.
- **Any check fails or cannot be confirmed** (amount mismatch, task Blocked, delivery
  not confirmed, or F&O unreachable): do not post. Present exactly what failed and the
  one question the person needs to answer to move forward. For an amount mismatch, the
  question is for a corrected or new vendor invoice; do not offer posting, an override,
  or partial payment as a way past the mismatch.

### Step 6: Post only on explicit confirmation (human-gated)

Post **only** after the person explicitly confirms in the conversation (for example
*"yes, post it"*). A summary is not consent; a question is not consent. On confirmation,
follow the `ep09-vendor-invoice-posting` procedure to post, through the ERP MCP **form
tools**, the two documents that record the spend against the already-confirmed PO:

1. the **product receipt** against the PO line (this creates the received quantity the
   three-way match needs), then
2. the **vendor invoice**, which books the expense and the accounts-payable liability.

Verify it posted (the PO flips to `Invoiced`), record the invoice and voucher numbers
back on the launch task for the audit trail, and report them to the person. If the
person does not confirm, or asks to hold, do nothing to the ledger.

The ERP MCP **OData / data tools** expose no post action; posting runs through the ERP
MCP **form tools**, which drive the F&O purchase-order, product-receipt, and
vendor-invoice forms the way a clerk would. That is why posting is a deliberate,
form-driven step a person authorizes, not a silent data write.

## What this skill is NOT

- It does **not** post without an explicit in-conversation confirmation. A person owns
  the go-ahead for every ledger post; the agent summarizes, asks, and waits.
- It does **not** mark work complete on its own. It sets a task to `Done` only on the
  person's explicit confirmation that the work was delivered, and it never overrides a
  `Blocked` task that way.
- It does **not** post an invoice that fails a check. An amount that does not match the
  PO line, or a launch task that is `Blocked`, stops the agent and turns it into a
  clarifying question, not a post. An amount mismatch can only be resolved by a
  corrected or new vendor invoice; the agent does not override it or partial-pay it.
- It does **not** invent figures. Every number is grounded in its source (the uploaded
  invoice, `lc_vendorwork` and `lc_task` in Dataverse, `PurchaseOrderLinesV2` in F&O).
  If F&O is unreachable, it holds and says so rather than guessing.
- It is **not** event-driven. There is no batch, no `lc_reconciliation` trigger row, and
  no autonomous wake-up. The uploaded invoice is the trigger and the posted F&O invoice
  is the only artifact.
