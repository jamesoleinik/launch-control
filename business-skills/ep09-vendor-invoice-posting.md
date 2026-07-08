# Vendor Invoice Posting (human-approved, closes a reconciled launch procurement gap)

## Description

The Season 2 / Episode 9 companion to the reconciliation skill
(`ep09-vendor-invoice-reconciliation`). Reconciliation stops at a drafted follow-up
and hands the ledger to a human: it never posts. This skill is that human-gated next
step, written down so it is auditable and reversible. Given a reconciliation outcome
that a person has **approved**, it posts the Finance & Operations ledger voucher that
records the outstanding vendor invoice (the expense and the accounts-payable
liability) for the gap, verifies it landed, and can reverse it cleanly. It is the
authorized posting the Act 5 agent is forbidden to do on its own: the agent drafts and
a human runs this, or an operator runs it after approving the agent's outcome.

The procedure below is the one validated end to end against the `dat` legal entity: a
25,000 gap on PO-10502 (Contoso Supply Co, vendor `V0001`) was posted as a real
voucher and then reversed to leave the ledger net zero.

## Instructions

### Step 0: Require an approved reconciliation outcome (GUARDRAIL)

Do not post anything until a human has approved the reconciliation outcome for this
gap. The input to this skill is an approved `lc_reconciliation` outcome (or an operator
instruction that names the launch, vendor, PO, and outstanding amount and states that
posting is approved). If approval is absent, stop and return to reconciliation. Posting
to the ledger without recorded human approval is out of policy, exactly as the
reconciliation skill states.

Take from the approved outcome: the PO number, the vendor account, the outstanding
(gap) amount, the launch and task it belongs to, and the currency. These are the only
figures you post.

### Step 1: Confirm the posting prerequisites in F&O (company `dat`)

Post into the `dat` legal entity (company `DAT`); every Launch Control PO, vendor, and
invoice lives there. Using the Dynamics 365 ERP MCP, confirm the Config layer that
makes a ledger post possible. If any item is missing, stop and run the Act 2 Config
build first; do not improvise ledger setup mid-post.

- **Ledger wired:** `Ledgers(LegalEntityId='dat')` has an accounting currency, a chart
  of accounts, and a fiscal calendar, and the transaction date falls in an open fiscal
  period.
- **Account structure active and assigned:** the account structure (for example
  `LC-PL`) reads `Status` = `Active` in `AccountStructures`, and it is assigned to the
  ledger (`Ledgers.AccountStructureName1`). A `Draft` structure cannot post; activation
  runs as a batch job and needs at least one allowed-value row.
- **Number sequences present:** posting a general ledger journal needs, at minimum, a
  journal batch number (`LedgerJournalId`) and a general-ledger entry number
  (`GeneralJournalEntryJournalNumber`) bound as references for `dat`
  (`NumberSequencesV2References`), plus a voucher number sequence for the journal name.
  A bare legal entity has none of these; provision them (see
  `scripts/python/setup_fno_number_sequences.py` for the pattern) before posting.
- **Dimensions active for data entities:** ledger lines created over OData require the
  financial dimensions to be activated for integrating applications
  (`DimensionAttributeActivations`, `DoActivate` = `Yes`) and an active ledger
  dimension format (`DimensionIntegrationFormats`,
  `DimensionFormatType` = `DataEntityLedgerDimensionFormat`, `IsActive` = `Yes`; for a
  main-account-only chart the format is `MainAccount`). Without these, line creation
  fails with "Only active dimensions can be used" or "No active format for data
  entities has been set up."

### Step 2: Create the vendor invoice journal (header and one line)

Use a general journal (`LedgerJournalType` = `Daily`) whose journal name carries a
vendor-invoice voucher series. Create it once and reuse it.

1. **Journal name** (`JournalNames`): `Type` = `Daily`, `VoucherSeriesCode` = the
   vendor-invoice voucher sequence (for example `Vvch_1`). Confirm `VoucherSeries`
   (the resolved series) is non-zero after create; a name with no voucher series fails
   posting with "a number sequence reference is missing".
2. **Header** (`LedgerJournalHeaders`): set `JournalName` and a `Description` that
   names the PO and vendor (for example `LC reconcile PO-10502 V0001`). The
   `JournalBatchNumber` auto-assigns from `LedgerJournalId`; do not set it by hand
   (insert is not allowed on that field).
3. **Line** (`LedgerJournalLines`), recording the invoice as expense plus AP liability:
   - `AccountType` = `Ledger`, `AccountDisplayValue` = the accounts-payable summary
     account (for example `200100`), `CreditAmount` = the outstanding gap amount.
   - `OffsetAccountType` = `Ledger`, `OffsetAccountDisplayValue` = the expense account
     (for example `618100`).
   - `CurrencyCode` = the outcome currency (for example `USD`), `TransDate` = a date in
     an open period, `Invoice` = the vendor invoice reference (for example
     `INV-PO-10502`), `Text` = the same PO / vendor description.

   This posts a debit to expense and a credit to accounts payable for the gap amount,
   which is what a vendor invoice records. (A vendor sub-ledger line, `AccountType`
   `Vend` with a posting profile, is the fuller form but needs additional AP number
   sequences that a bare demo entity lacks; the ledger-to-ledger line above is the
   reliable, self-contained posting for this build.)

### Step 3: Post the journal

The ERP MCP OData surface exposes no post action, so post through the journal form.
Open the `LedgerJournalTable` form (Display) in `dat`, select the journal row (marked),
and click `Post`. Posting runs as a background operation: poll
`__TimerForAsyncTaskPolling` until it completes. Success reads "Number of vouchers
posted to the journal: 1" and the row flips `Posted` = yes with a posted timestamp.

Optionally click `Validate` (or `Simulate posting`) first; both surface any missing
number sequence or dimension setup before you commit.

### Step 4: Verify the posting landed

Read the posted line back (`LedgerJournalLines` for the batch): it now carries a
`Voucher` (for example `VVCH-000001`) with the expected credit to the AP account and
the offset debit to the expense account. That voucher is the evidence the gap-closing
invoice is on the ledger. Record the voucher number in the outcome for the audit trail.

### Step 5: Reverse when the post was a test or is superseded (revert)

A posted general-ledger voucher cannot be un-posted; you reverse it with a compensating
voucher so the two net to zero. Create a second journal on the same journal name whose
single line mirrors the original: `AccountType` `Ledger` = the AP account with
`DebitAmount` = the same amount, offsetting to the expense account. Post it the same
way (Step 3). The AP account and the expense account each net to zero across the two
vouchers, leaving the ledger as if nothing had posted. Use this to revert a validation
run, or to back out a posting that a later approval rescinds. Record both voucher
numbers.

### Step 6: Write the posting back to the signal (audit)

Using the Dataverse MCP, record on the reconciliation outcome (or the launch task) that
the invoice was posted, the voucher number, the amount, and who approved it, so the
launch plan and the ledger agree. This does not create or re-open a
`lc_reconciliation` row; it annotates the closed one for traceability.

## What this skill is NOT

- It is **not** something the autonomous agent runs unprompted. It requires recorded
  human approval of a reconciliation outcome first; without approval, stop. The Act 5
  agent still refuses to post on its own.
- It does **not** replace the reconciliation skill. Reconciliation decides whether a gap
  is real and material and drafts the follow-up; this skill is only the approved posting
  that follows, plus its reversal.
- It does **not** improvise ledger configuration. If the Config layer (ledger wiring,
  active and assigned account structure, number sequences, active dimensions) is
  missing, it stops and defers to the Act 2 Config build rather than half-configuring
  Finance & Operations to force a post.
- It does **not** leave test postings on the ledger. A validation or superseded post is
  reversed with a compensating voucher (Step 5) so the accounts net to zero.
