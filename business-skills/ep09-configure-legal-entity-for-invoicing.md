# Configure a Legal Entity for Invoicing (stand up the F&O Config layer through the ERP MCP)

## Description

The Season 2 / Episode 9 Business Skill that stands up the Finance & Operations
**Config layer** a bare legal entity needs before it can post a vendor invoice. It is
the governed, reusable form of Act 2's configuration work: instead of narrating "drive
the `form_*` tools in order," it encodes the dependency-ordered procedure the agent
reads and executes through the Dynamics 365 ERP MCP `data_*` and `form_*` tools, each
step grounded on the Microsoft Learn finance-and-operations configuration path.

The problem it solves: a freshly provisioned legal entity (for Launch Control, the `dat`
company) ships with currencies and some master data, but no ledger wiring, chart of
accounts, fiscal calendar, account structure, or vendor posting profile. Raw OData
cannot create those composite financial entities (they gate creation behind X++), so
they must be built through the ERP MCP. Until they exist, no vendor invoice can post.

This skill builds the six **transaction-enabling** Config items that
`scripts/validate_fno_scaffold.py` gates on, plus payment terms. It does **not** post an
invoice (that is `ep09-vendor-invoice-posting`) and it does **not** seed the demo master
data or the `lc_vendorwork` join (those are deterministic, idempotent scripts). It
configures the company; the validator certifies success; the scripts seed the data.

**The ground truth is the validator, not the agent.** After each layer, re-run
`scripts/validate_fno_scaffold.py --company <entity>` and trust its exit code (0 when
every transaction-enabling Config item is present, 1 otherwise). The agent does not
self-certify that the company is ready; the read-only validator does.

## What "ready to invoice" means (the gate)

`scripts/validate_fno_scaffold.py` treats these six Config items as transaction-enabling.
All must be present for the validator to exit 0 and for a vendor invoice to post:

1. Ledger accounting currency
2. Chart of accounts
3. Main accounts
4. Fiscal calendars (with open periods for the invoice date)
5. Account structures (active)
6. Vendor posting profiles

Payment terms are built alongside these; tax codes and released products are optional
for the vendor-engagement scenario (the POs are category-based, tax-free) and are left
as documented follow-ups, not gates.

## Entities and values (validated build)

Build order and the ERP MCP tool for each layer, with the reference values this build
used. All reads and writes target the target legal entity (for Launch Control,
`dataAreaId` / company `dat` / `DAT`); confirm the entity before writing.

| Layer | Object | Entity / form | Tool | Reference value |
| --- | --- | --- | --- | --- |
| Calendar | Fiscal calendar | `FiscalCalendarsEntity` | `data_*` | `LC` |
| Calendar | Fiscal years | `FiscalCalendarYearsEntity` | `data_*` | `2025`, `2026`, `2027` |
| Calendar | Fiscal periods | `FiscalPeriods` | `data_*` | `2026`: 1 Opening + 12 Operating |
| Accounts | Chart of accounts | `ChartOfAccounts` | `data_*` | `LC` (six-digit mask) |
| Accounts | Main accounts | `MainAccounts` | `data_*` | 11 AP-relevant accounts |
| Structure | Account structure | `AccountStructures` | `data_*` | `LC-PL` (single `MainAccount` segment) |
| Structure | Allowed values | `AccountStructureConstraints` | `data_*` | `Position` 1, `SegmentCriteria01` = `*` |
| Structure | Activation | `AccountStructureActivations` | `data_*` | `DoActivate` = `Yes` (async batch) |
| Ledger | Ledger wiring | `Ledgers(LegalEntityId='dat')` | `data_update` | `USD` / `LC` / `LC` |
| Profile | Vendor posting profile | `PostingProfileHeaders` + `PostingProfileLines` | `data_*` | `LC` (summary `200100`, settlement `100100`, accrual `200150`) |
| Terms | Payment terms | `PaymentTerms` | `data_*` | `Net30`, `Net45` |

The 11 main accounts span the account types a vendor-invoice post touches: bank
(`100100`), sales tax receivable (`140100`), accounts payable (`200100`), purchase
accrual (`200150`), retained earnings (`300100`), revenue (`401100`), purchase
expenditure (`600100` / `600150`), vendor cash discount (`600200`), consulting expense
(`618100`), and rounding (`801100`).

## Instructions

### Step 0: Confirm the legal entity, then read the live gap

Confirm the target legal entity before writing anything (for Launch Control, `dat`).
Then run the read-only validator to see exactly what is missing:

```
$env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
python episodes/ep-09-dataverse-fno/scripts/validate_fno_scaffold.py --company dat
```

On a bare entity it exits 1 with the six Config items MISSING. Build them in the order
below, re-running the validator after each layer, and stop when it exits 0. Do not
improvise a different sequence: the dependencies are real (the ledger cannot reference a
chart or calendar that does not exist yet, and the account structure must be activated
before it can be assigned).

Ground each step on the Microsoft Learn finance-and-operations configuration path
(global address book, then currencies and the ledger, then chart of accounts and main
accounts, fiscal calendar and periods, account structure, then Accounts Payable posting
profiles and terms) rather than improvising the values from generic knowledge.

### Step 1: Fiscal calendar and open periods (`data_*`)

If no shared fiscal calendar exists to reuse (survey `FiscalCalendarsEntity`,
`FiscalCalendarYears`, `FiscalPeriods` first), build one through the `data_*` tools:

- Create calendar `LC` on `FiscalCalendarsEntity`.
- Create fiscal years `2025`, `2026`, `2027` on `FiscalCalendarYearsEntity` (Jan 1 to
  Dec 31 each). Creating the year header does **not** auto-generate periods.
- Create the `2026` periods explicitly on `FiscalPeriods`: one `Opening` period plus
  twelve monthly `Operating` periods (`Period 1`..`Period 12`), with quarter and month
  enums set. The invoice date must fall in an open Operating period.

### Step 2: Chart of accounts and main accounts (`data_*`)

If no shared chart exists to reuse, build one through the `data_*` tools:

- Create chart `LC` on `ChartOfAccounts` (six-digit main-account mask).
- Create the 11 AP-relevant main accounts on `MainAccounts` (the accounts listed in
  Entities and values above). These are the minimum a vendor-invoice posting and its
  reversal touch.

### Step 3: Account structure, built and activated (`data_*`, async)

The account structure cannot be fully stood up through a single data entity: on create,
`StructureType` is rejected by OData and `Status` is read-only, so a create lands as
`Draft`. Use the data-entity path (cleaner than the `form_*` grid, which does not
surface a "New row" action for the allowed-values grid):

- Create draft structure `LC-PL` on `AccountStructures` with a single `MainAccount`
  segment.
- Add an allowed-value row on `AccountStructureConstraints`: `Position` 1,
  `SegmentCriteria01` = `*` (all main accounts allowed). A single-segment structure
  still needs at least one allowed-value row.
- Create `LC-PL` on `AccountStructureActivations` with `DoActivate` = `Yes`. This
  **queues** the activation as an F&O batch job; the row moves `Draft` -> `Activating`
  -> `Active` once the batch server runs it. Activation completes asynchronously, so do
  not block on it; the ledger's `AccountStructureName1` is assigned in Step 4 once the
  structure is `Active`.

(The `form_*` alternative: drive `DimensionConfigureAccountStructure`, select `LC-PL`,
click **Activate**, and confirm the dialog. The data-entity path above is preferred
because it also creates the allowed-value row the grid will not.)

### Step 4: Wire the ledger (`data_update`)

The bare `dat` ledger row already exists with empty references. Update it through
`data_update_entities` on `Ledgers(LegalEntityId='dat')`:

- `AccountingCurrency` = `USD`, `ReportingCurrency` = `USD` (USD ships with the env).
- `ChartOfAccounts` = `LC`.
- `FiscalCalendar` = `LC`.
- Once `LC-PL` is `Active` (Step 3 completes on the batch server), set
  `AccountStructureName1` = `LC-PL`.

Verify the `dat` ledger reports accounting currency `USD`, chart `LC`, calendar `LC`.

### Step 5: Vendor posting profile (`data_*`)

Build the Accounts Payable posting profile through the `data_*` tools:

- Create profile `LC` for `dat` on `PostingProfileHeaders`.
- Add the default `All` line on `PostingProfileLines` with summary (AP) account
  `200100`, settlement / liquidity `100100`, and arrival / accrual `200150` (set via the
  `*DisplayValue` fields).
- Set `LC` as the default posting profile in Accounts Payable parameters
  (`VendorParameters(dataAreaId='dat').PostingProfile`) so a live post resolves it.

### Step 6: Payment terms (`data_*`), and the optional follow-ups

- Create `Net30` and `Net45` on `PaymentTerms` for `dat`.
- **Tax codes (optional):** a `TaxCode` needs a ledger posting group, a settlement
  period, a tax authority, and tax ledger accounts, a chain not cleanly OData-exposed
  here. The vendor-engagement scenario posts tax-free, so leave tax codes as a follow-up.
  They are not a transaction-enabling gate.
- **Released products (optional):** the vendor-engagement POs are category-based
  (procurement categories, not stocked items), so released products are not required.
  Leave them as a follow-up.

### Step 7: Confirm the gate, then hand off to posting

Re-run the validator and confirm it exits 0:

```
python episodes/ep-09-dataverse-fno/scripts/validate_fno_scaffold.py --company dat
# Config layer complete: 'dat' can create/post vendor invoices.
```

The company is now ready to invoice. The remaining posting prerequisites specific to an
authentic vendor-invoice cycle (the AP and inventory number sequences, including the
easy-to-miss `SubledgerJournalNum`, provisioned by
`scripts/python/setup_fno_number_sequences.py`; the inventory posting "Purchase
expenditure for expense" account; and, for a stocked path, released products) are owned
by `ep09-vendor-invoice-posting` Step 1, not repeated here. Hand off to that skill for
the confirmed, human-gated post.

## What this skill is NOT

- It does **not** post an invoice or a journal. It only stands up the Config layer that
  makes a post possible; the confirmed, human-gated post is `ep09-vendor-invoice-posting`.
- It does **not** seed demo master data or the `lc_vendorwork` join. That fixed data is
  built by the idempotent scripts (`seed_vendor_work.py`, `erp_mcp_write.py`), not by
  this skill. This skill configures the company; the scripts populate it.
- It does **not** self-certify readiness. `scripts/validate_fno_scaffold.py` is the
  ground truth; the agent builds a layer, re-runs the validator, and trusts its exit
  code rather than asserting the company is ready.
- It does **not** improvise the financial values from generic knowledge. Each layer is
  grounded on the Microsoft Learn finance-and-operations configuration path and the
  reference values above, built in dependency order.
- It is **not** a substitute for demo data. If configuring a bare company is not wanted
  (for example on camera), provision the environment with a configured demo company and
  point the validator at it (`--company USMF`) instead; this skill is for the
  build-from-bare path.
