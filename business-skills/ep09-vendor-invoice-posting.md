# Vendor Invoice Posting (confirmed post that records a reconciled vendor invoice)

## Description

The Season 2 / Episode 9 companion to the reconciliation skill
(`ep09-vendor-invoice-reconciliation`). Reconciliation runs the two checks (the invoice
matches the PO line in F&O, and the launch task is complete in Dataverse) and, when both
pass, asks the person to confirm the post. This skill is that confirmed next step,
written down so it is auditable and reversible. Given a reconciliation the person has
**confirmed in the conversation**, it posts the real Finance & Operations vendor invoice
that records the vendor spend (the expense and the accounts-payable liability), verifies
it landed, and can reverse it cleanly. The reconciliation agent invokes this only after
an explicit go-ahead; a person always authorizes the post.

The procedure below is the one validated end to end against the `dat` legal entity: a
25,000 gap on PO-10502 (Contoso Supply Co, vendor `V0001`) was carried through the
authentic **purchase order -> product receipt -> vendor invoice** cycle and **posted**
as a real vendor invoice (`INV-PO-10502`), which flipped PO-10502 to `Invoiced` and
booked the accounts-payable liability. This is the Microsoft-documented Accounts
Payable path (see
[Vendor invoices overview](https://learn.microsoft.com/dynamics365/finance/accounts-payable/vendor-invoices-overview)),
not a general-ledger journal stand-in.

## Instructions

### Step 0: Require an explicit confirmation to post (GUARDRAIL)

Do not post anything until the person has confirmed the post in the conversation. The
input to this skill is a reconciliation that passed both checks and an explicit
go-ahead (for example *"yes, post it"*), or an operator instruction that names the
launch, vendor, PO, and amount and states that posting is confirmed. A summary is not
consent and a question is not consent. If confirmation is absent, stop and return to
reconciliation. Posting to the ledger without a recorded go-ahead is out of policy,
exactly as the reconciliation skill states.

Take from the confirmed reconciliation: the PO number, the vendor account, the invoice
amount, the launch and task it belongs to, and the currency. These are the only figures
you post.

### Step 1: Confirm the posting prerequisites in F&O (company `dat`)

Post into the `dat` legal entity (company `DAT`); every Launch Control PO, vendor, and
invoice lives there. Using the Dynamics 365 ERP MCP, confirm the Config layer that
makes a vendor-invoice post possible. If any item is missing, stop and run the Act 2
Config build first; do not improvise ledger setup mid-post. The authentic vendor
invoice draws on **more** setup than a bare GL journal, and each gap surfaces as a
distinct, and often generic, F&O error. The full list validated for this build:

- **Ledger wired:** `Ledgers(LegalEntityId='dat')` has an accounting currency, a chart
  of accounts, and a fiscal calendar, and the invoice date falls in an open fiscal
  period.
- **Procurement product category (for category / non-stocked lines):** because no
  released products exist, the invoiceable PO line is a **category-based** line. A
  procurement category hierarchy (`LCProc`), a procurement category (for example
  "Video Production Services"), and a unit of measure (for example `ea`) must exist so
  the line can be created, received, and invoiced.
- **Number sequences present and correctly configured** (`NumberSequencesV2References`
  bound for `dat`, provisioned via `scripts/python/setup_fno_number_sequences.py`):
  - `PurchaseOrderVoucher`, `PurchInvoiceVoucher`, `PurchPackingSlipVoucher`, and the
    internal purchase ids the cycle assigns.
  - `InventTransId` (inventory transaction id, for example series `Itrn_1`) so the
    category line gets an inventory transaction.
  - `ParmId` (for example `Parm_1`) **with `Continuous` = No** for this environment;
    a `Continuous` = Yes setting is rejected on post with *"System does not support
    setup 'continuous' of number sequence ..."*.
  - `SubledgerJournalNum` (for example series `Sslj_1`). **This one is easy to miss.**
    Without it, posting fails with the generic *"Numbers could not be generated
    because a number sequence reference is missing"* and F&O does not name the
    datatype. It is a General ledger-area datatype that every subledger post (including
    a vendor invoice) needs; provision the sequence and its reference at DataArea /
    `dat` scope.
- **Accounts Payable default posting profile:** `VendorParameters(dataAreaId='dat')`
  `.PostingProfile` must name a vendor posting profile (for example `LC`, whose line
  posts the AP summary account `200100` and settlement `100100`). Missing, the post
  fails with *"Posting profile has not been set up in accounts payable parameters."*
- **Inventory posting ledger account for the expense:** Inventory management > Setup >
  Posting > Posting, **Purchase order** tab, posting type **"Purchase expenditure for
  expense"** must map to a main account (for example expense account `618100`, Item
  code = `All`). Missing, the post fails validation with *"Account number for
  transaction type Purchase expenditure for expense does not exist."* This is the
  category-line analogue of the stocked-item "Purchase expenditure for product"
  account.

> Reproducibility: the number-sequence pieces (`Itrn_1`, `Parm_1` non-continuous,
> `Sslj_1`, and the purchase / inventory voucher series) are provisioned by
> `scripts/python/setup_fno_number_sequences.py` (idempotent, `--dry-run` first). The
> posting profile default and the inventory posting ledger account are one-time Config
> steps recorded in `episodes/ep-09-dataverse-fno/ACT2-RUN-LOG.md`.

### Step 2: Post the product receipt against the confirmed PO (form tools)

The invoiceable PO line and the PO **confirmation** are pre-staged in Act 2 (the line is
created over OData and the PO is confirmed to `PurchaseOrderStatus` = `Confirmed`), so
the agent does not create or confirm the line live. What the agent posts live is the
**product receipt**, which flips the line to `Received` and creates the received
quantity the three-way match needs before the vendor invoice can post.

Run this through the ERP MCP **form tools** in a single session (form state does not
persist across separate ERP MCP calls, so the whole sequence must be one script):

1. Open the purchase order list page (`form_open_menu_item`, `PurchTableListPage`,
   Display, company `DAT`).
2. Filter the grid to the target PO (`form_filter_grid`, grid `Grid`, column
   `PurchTable_PurchIdAdvanced`, value the PO number, for example `PO-10514`).
3. Select the row (`form_select_grid_row`, grid `Grid`, row `0`, marking `Marked`; this
   grid requires the marking parameter).
4. Click **Product receipt** (`form_click_control`, control `buttonUpdatePackingSlip`).
   This opens the **Posting product receipt** dialog (form `PurchEditLines`).
5. In the dialog, set the quantity basis to receive the full ordered quantity
   (`form_set_control_values`: combobox `SpecQty` = `Ordered quantity`, its default) and
   set the **Product receipt** number (`form_set_control_values`: `PurchParmTable_Num` =
   the vendor packing-slip id, for example `PR-PO-10514`).
6. Click **OK** (`form_click_control`, control `OK`). Posting runs as a background
   operation; poll `__TimerForAsyncTaskPolling` until it completes.

The line status now reads `Received`, and the PO exposes the **Invoice**
(`buttonUpdateInvoice`) path used next.

### Step 3: Create the vendor invoice draft in the Pending vendor invoices workspace

Create the vendor invoice **from** the purchase order / product receipt so it is fully
matched:

1. Open the **Pending vendor invoices** list page (`VendInvoiceInfoListPage`, Display)
   in `dat`. This is the reliable surface for both drafting and posting; the
   `VendEditInvoice` edit form hides its Post button after navigation.
2. Create the invoice from the PO (`From purchase order`) or product receipt, set the
   vendor invoice number (`InvoiceDetails_Num`, for example `INV-PO-10502`) and the
   invoice date (`InvoiceDetails_DocumentDate`). Confirm totals via the `Totals`
   (`ParmTableTotals`) dialog: subtotal and invoice amount equal the gap, correct
   currency.
3. The draft now appears in the workspace with **Last match status = Passed**
   (quantity and price matched to the PO and product receipt). This is the state the
   agent's reconciliation hands off for human approval; it is visibly populated in the
   workspace.

### Step 4: Simulate, then post

1. Select the draft row (marked) and click **Simulate posting** (`buttonSimulatePosting`).
   It runs the full posting validation without committing. Poll
   `__TimerForAsyncTaskPolling` until it completes, then open **Results of posting
   simulation** (`ResultsOfPostingSimulation`) to read any failure detail. Iterate on
   Step 1 setup until the result reads **Passed**. (This is how the missing
   `SubledgerJournalNum` reference and the missing "Purchase expenditure for expense"
   account were each identified for this build.)
2. With simulation Passed, select the row again and click **Post** (`Post`). Posting
   runs as a background operation; poll `__TimerForAsyncTaskPolling` until it reports
   *"The vendor invoice posting process is complete for vendor `<V>`, invoice `<num>`."*
   The draft leaves the Pending vendor invoices workspace once it posts through.

### Step 5: Verify the posting landed

- **PO status:** `PurchaseOrderHeadersV2` for the PO now reads
  `PurchaseOrderStatus` = `Invoiced` (was `Confirmed`). This is the primary,
  entity-readable proof.
- **Posted invoice + voucher:** Accounts payable > Inquiries and reports > Invoice >
  **Invoice journal** shows the posted invoice and its ledger voucher (Dr expense
  `618100` / Cr AP summary `200100`).
- **Open AP liability:** the vendor's **Transactions** (Accounts payable > Vendors >
  All vendors > `V0001` > Transactions) shows the open invoice transaction for the gap
  amount.
- **Pending workspace cleared:** the draft no longer appears in **Pending vendor
  invoices**, because it posted.

Record the invoice number and voucher on the outcome for the audit trail.

### Step 6: Reverse only if the post was a throwaway test (revert)

If this posting was purely a validation run and must be backed out, reverse it with a
**vendor credit note** against the same invoice (Accounts payable > credit note flow),
which nets the AP liability and expense to zero and leaves the PO history intact. Do
**not** reverse a posting that records a confirmed, real invoice. (For the recorded demo
the posted invoice is left in place as proof; see the recording prompt below.)

### Step 7: Write the posting back to the launch task (audit)

Using the Dataverse MCP, record on the launch task (`lc_task`, and optionally the
`lc_vendorwork` engagement) that the invoice was posted, the invoice and voucher
numbers, the amount, and who confirmed it, so the launch plan and the ledger agree.
There is no `lc_reconciliation` row in this design; the launch task and the posted F&O
invoice are the record.

## Proving it in the recording (agent prompt + ERP deep-links)

To demonstrate on camera that the confirmed posting is real, ask the agent the prompt
below and then open the ERP screen it should have affected. Deep-links follow the
pattern `<fno-operations-url>/?cmp=DAT&mi=<MenuItem>` (substitute your F&O operations
URL; do not commit the literal environment URL).

**Prove-it agent prompt:**

> *Yes, post it. Post the vendor invoice for PO-10502 (Contoso Supply Co, vendor V0001,
> Q3 launch video task) through the purchase order to product receipt to vendor invoice
> cycle, then confirm it posted by showing me the purchase order status and the posted
> invoice voucher.*

**ERP screens to confirm (open after the agent runs):**

| What to confirm | Menu item (`mi=`) |
|---|---|
| Purchase order list (PO-10502 = Invoiced) | `PurchTableListPage` |
| Pending vendor invoices (draft cleared after post) | `VendInvoiceInfoListPage` |
| Posted vendor invoices / invoice journal + voucher | `VendInvoiceJournal` |
| Inventory posting profiles (expense ledger account) | `InventPosting` |

Example (PO list): `<fno-operations-url>/?cmp=DAT&mi=PurchTableListPage`.

## What this skill is NOT

- It is **not** something the agent runs unprompted. It requires an explicit
  in-conversation confirmation to post first; without a go-ahead, stop. The agent never
  posts on its own.
- It does **not** replace the reconciliation skill. Reconciliation runs the two checks
  (amount matches the PO line, task is complete) and asks for confirmation; this skill is
  only the confirmed posting that follows, plus its reversal.
- It does **not** improvise ledger configuration. If the Config layer (ledger wiring,
  procurement category, number sequences including `SubledgerJournalNum`, AP posting
  profile, and the inventory posting expense account) is missing, it stops and defers to
  the Act 2 Config build rather than half-configuring Finance & Operations to force a
  post.
- It does **not** post a general-ledger journal in place of a vendor invoice. The
  earlier GL-journal approach is superseded; this skill posts the authentic,
  PO-matched vendor invoice through the Accounts Payable cycle.
