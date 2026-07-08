# Act 2 run log: populating the `dat` legal entity through the ERP MCP

This log records a live attempt to stand up the F&O Config layer on the bare `dat`
legal entity using the Dynamics 365 ERP MCP `form_*` / `data_*` tools, driven from the
GitHub Copilot CLI after the ERP MCP server was registered in the session.

Environment identifiers are resolved from `.env` and omitted here.

## Starting state (validate_fno_scaffold.py)

| Layer | Object | Count | Status |
| --- | --- | --- | --- |
| Config | Ledger accounting currency | 0 | MISSING |
| Config | Chart of accounts | 0 | MISSING |
| Config | Main accounts | 0 | MISSING |
| Config | Fiscal calendars | 0 | MISSING |
| Config | Account structures | 0 | MISSING |
| Config | Vendor posting profiles | 0 | MISSING |
| Config | Payment terms | 0 | MISSING |
| Config | Tax codes | 0 | MISSING |
| Config | Currencies | 3 | present |
| Config | AP number sequence references | 14 | present |
| Master | Vendor groups | 1 | present |
| Master | Vendors | 3 | present |
| Master | Released products | 0 | MISSING |
| Master | Purchase orders | 7 | present |
| Txn | Product receipts | 0 | MISSING |
| Txn | Vendor invoices | 0 | MISSING |

Validator exit code 1: 6 transaction-enabling Config items missing.

Surveyed shared config via ERP MCP `data_find_entities_sql`: no shared charts of
accounts (`ChartOfAccounts` empty), no fiscal calendars (`FiscalCalendarsEntity`
empty). The `dat` Ledger form confirms empty Chart of accounts, Fiscal calendar,
Account structures grid, and Accounting currency, all of which must be built first.

## Build steps

### 1. Fiscal calendar (done)

The bare environment had no fiscal calendar to reuse (data entity survey returned
zero rows for `FiscalCalendarsEntity`, `FiscalCalendarYears`, and `FiscalPeriods`),
so the calendar was built directly through the ERP MCP `data_*` tools:

- `data_create_entities` on `FiscalCalendarsEntity`: created calendar `LC`
  ("Launch Control fiscal calendar").
- `data_create_entities` on `FiscalCalendarYearsEntity`: created fiscal years
  `2025`, `2026`, `2027` (Jan 1 to Dec 31 each). Creating the year header does not
  auto-generate periods through the data entity.
- `data_create_entities` on `FiscalPeriods`: created the `2026` periods explicitly:
  one `Opening` period plus twelve monthly `Operating` periods (`Period 1`..
  `Period 12`), quarter and month enums set. 13 rows created.

Result: `FiscalCalendarsEntity` count is now 1, so the validator's "Fiscal
calendars" Config item flips to present, and `2026` has posting-ready operating
periods.

### 2. Chart of accounts + main accounts (done)

Also built through the `data_*` tools (no shared chart existed to reuse):

- `data_create_entities` on `ChartOfAccounts`: created chart `LC` ("Launch Control
  chart of accounts", six-digit main-account mask).
- `data_create_entities` on `MainAccounts`: created 11 AP-relevant main accounts
  spanning the account types a vendor-invoice posting touches: bank (`100100`),
  sales tax receivable (`140100`), accounts payable (`200100`), purchase accrual
  (`200150`), retained earnings (`300100`), revenue (`401100`), purchase
  expenditure (`600100`/`600150`), vendor cash discount (`600200`), consulting
  expense (`618100`), and rounding (`801100`).

Result: `ChartOfAccounts` and `MainAccounts` Config items flip to present.

### 3. Account structure (built + activation queued)

Account structures cannot be fully stood up through the data entity (the
`StructureType` property is rejected by OData and `Status` is read-only on create,
so a create lands as `Draft`). The hybrid path used:

- `data_create_entities` on `AccountStructures`: created draft structure `LC-PL`
  with a single `MainAccount` segment (all main accounts allowed).
- ERP MCP `form_*` tools then drove the "Configure account structures"
  (`DimensionConfigureAccountStructure`) form: selected the `LC-PL` row, clicked
  **Activate**, and confirmed the activation dialog. F&O queued the activation as a
  batch job ("The Activate account structure LC-PL job is added to the batch
  queue") and the row moved to status **Activating**, which becomes **Active** once
  the batch server runs the job.

Result: `AccountStructures` Config item flips to present; activation completes
asynchronously.

### 4. Ledger wiring (currency, COA, calendar set; structure assignment pending)

The bare `dat` ledger row already existed but with empty references. Updated it via
`data_update_entities` on `Ledgers(LegalEntityId='dat')`:

- `AccountingCurrency` = `USD`, `ReportingCurrency` = `USD` (USD ships with the
  environment).
- `ChartOfAccounts` = `LC`.
- `FiscalCalendar` = `LC`.

Verified: the `dat` ledger now reports accounting currency `USD`, chart `LC`,
calendar `LC`. This flips the validator's "Ledger accounting currency" Config item
to present.

Activation (account structure): activating `LC-PL` needs an allowed-value row (a
single `MainAccount` segment needs at least one row, e.g. a `*` wildcard). The ERP
MCP form interface for `DimensionConfigureAccountStructure` exposes "Add segment"
(adds a dimension column) but does not surface a grid-level "New row" action for the
allowed-values grid, and the `Level1` cell is not editable without an existing row.
The clean path was the data entities instead:

- `data_create_entities` on `AccountStructureConstraints`: added a `Draft` allowed-
  value row for `LC-PL` at `Position` 1 with `SegmentCriteria01` = `*` (all main
  accounts allowed).
- `data_create_entities` on `AccountStructureActivations`: created `LC-PL` with
  `DoActivate` = `Yes`, which queues the activation batch. Activation runs
  asynchronously (the row moves `Draft` -> `Activating` -> `Active` once the batch
  server processes it), after which `AccountStructureName1` can be assigned on the
  ledger.

### 5. Vendor posting profile (done)

`PostingProfileHeaders`/`PostingProfileLines` are the vendor posting profile
("Vendor posting profile" / "Vendor ledger accounts"). Built through `data_*`:

- `data_create_entities` on `PostingProfileHeaders`: created profile `LC` for `dat`.
- `data_create_entities` on `PostingProfileLines`: added the default `All` line with
  summary (AP) account `200100`, settlement/liquidity `100100`, and arrival/accrual
  `200150` via the `*DisplayValue` fields.

### Validator checkpoint: Config layer complete

With the vendor posting profile present, `validate_fno_scaffold.py --company dat`
now reports every transaction-enabling Config item present and exits 0:

```
Config  Ledger accounting currency           1  present
Config  Chart of accounts                     1  present
Config  Main accounts                        11  present
Config  Fiscal calendars                      1  present
Config  Account structures                    1  present
Config  Vendor posting profiles               1  present
...
Config layer complete: 'dat' can create/post vendor invoices.
```

Remaining non-blocking gaps: payment terms, tax codes, released products (added
next), plus the transaction outputs (product receipts, vendor invoices) that Act 2's
batch and agent produce. The `LC` posting profile should also be set as the default
in Accounts payable parameters for live posting.

### 6. Payment terms (done), tax codes + released products (optional, documented)

- `data_create_entities` on `PaymentTerms`: created `Net30` and `Net45` for `dat`.
- Tax codes: a `TaxCode` requires a ledger posting group and a settlement period
  (and behind those a tax authority and tax ledger accounts). That chain is not
  cleanly OData-exposed here, and the vendor engagement scenario posts tax-free, so
  tax codes are left as an optional follow-up rather than built. This does not block
  the validator (tax codes are not a transaction-enabling item).
- Released products: creating a `ReleasedProductsV2` row needs a full product master
  (item model group, item/procurement category, and storage/tracking dimension
  groups). The vendor engagement POs are category-based (procurement categories, not
  stocked items), so released products are also optional for this scenario and left
  as a follow-up.

### Final state

`validate_fno_scaffold.py --company dat` exits 0: all six transaction-enabling
Config items are present, so `dat` can create/post a vendor invoice. The only piece
that finishes asynchronously is account-structure activation (`LC-PL` moves to
`Active` when the F&O batch server runs the queued activation job); once active it
can be assigned to the ledger's `AccountStructureName1`. Everything else (fiscal
calendar + periods, chart of accounts + main accounts, ledger currency/COA/calendar,
vendor posting profile + AP summary account, payment terms) was built headlessly
through the ERP MCP `data_*` and `form_*` tools in this single session.

Objects built this run, all via the Dynamics 365 ERP MCP:

| Object | Entity / form | Count |
| --- | --- | --- |
| Fiscal calendar | `FiscalCalendarsEntity` | 1 (`LC`) |
| Fiscal years | `FiscalCalendarYearsEntity` | 3 (2025-2027) |
| Fiscal periods (2026) | `FiscalPeriods` | 13 |
| Chart of accounts | `ChartOfAccounts` | 1 (`LC`) |
| Main accounts | `MainAccounts` | 11 |
| Account structure | `AccountStructures` + `AccountStructureConstraints` + `AccountStructureActivations` | 1 (`LC-PL`, activating) |
| Ledger wiring | `Ledgers(dat)` | USD / `LC` / `LC` |
| Vendor posting profile | `PostingProfileHeaders` + `PostingProfileLines` | 1 (`LC`) |
| Payment terms | `PaymentTerms` | 2 (`Net30`, `Net45`) |

## Invoice-posting test: validating the human-approved posting skill

After the Config layer completed, the authorized vendor-invoice posting that the Act 5
agent is forbidden to do on its own was tested end to end against `dat`, and the
`business-skills/ep09-vendor-invoice-posting.md` skill was written from and then
re-validated against that run. The scenario is the reconciliation gap: 25,000
outstanding on PO-10502 (Contoso Supply Co, vendor `V0001`).

### Prerequisites provisioned to reach a postable state

Standing up the Config layer was necessary but not sufficient to post a general
journal; three additional prerequisites surfaced (each a hard blocker) and were
provisioned through the ERP MCP:

- **Account structure activated and assigned.** The queued `LC-PL` activation batch
  ran to completion (status `Active`), then `Ledgers(LegalEntityId='dat')`
  `AccountStructureName1` was set to `LC-PL`.
- **Two number sequences bound for `dat`** (`SequenceV2Tables` code +
  `NumberSequencesV2References`): `LedgerJournalId` (journal batch number) and
  `GeneralJournalEntryJournalNumber` (GL entry number). A general journal will not
  post without both; the symptom is the generic "a number sequence reference is
  missing" during Validate or Post even for a pure ledger-to-ledger line.
- **Dimensions activated for data entities.** `DimensionAttributeActivations`
  (`DoActivate` = `Yes`) plus an active `DimensionIntegrationFormats` row of type
  `DataEntityLedgerDimensionFormat` with format `MainAccount`. Without these,
  OData line creation fails with "Only active dimensions can be used" then "No active
  format for data entities has been set up."

A `Daily` general-journal name `LCGENJ` was created with a vendor-invoice voucher
series (`Vvch_1`).

### First posting run (skill authored from this)

- Created header on `LCGENJ` and one ledger-to-ledger line: Cr accounts payable
  `200100` 25,000, offset Dr expense `618100`, USD, `TransDate` in an open 2026 period.
- Posted through the `LedgerJournalTable` form (Post -> poll
  `__TimerForAsyncTaskPolling` -> "Number of vouchers posted to the journal: 1"):
  journal `LEDJ-000001`, voucher **VVCH-000001**.
- Reversed with a compensating mirror journal (Dr `200100` / Cr `618100`, 25,000):
  journal `LEDJ-000006`, voucher **VVCH-000006**. Accounts `200100` and `618100` each
  net to zero.

The ledger-to-ledger line was chosen over a vendor sub-ledger line (`AccountType`
`Vend` + posting profile) because the sub-ledger path needs additional AP number
sequences a bare demo entity lacks; the skill documents that tradeoff.

### Skill re-validation run (zero reconfiguration)

To prove the skill is reproducible, the whole procedure was re-run against the
now-provisioned environment with no setup changes:

- Posted journal `LEDJ-000007` (Cr `200100` / Dr `618100`, 25,000) via the form: one
  voucher posted, `Posted` = yes.
- Reversed with journal `LEDJ-000008` (Dr `200100` / Cr `618100`, 25,000): one voucher
  posted. Read back through `data_find_entities_sql`, the pair nets to zero on both
  the AP account and the expense account.

The re-run needed no reconfiguration, confirming every prerequisite the skill documents
(ledger wiring, active + assigned account structure, the two number sequences, active
dimensions, a voucher-series journal name) is in place and the posting/reversal
procedure is repeatable. The ledger is left clean (all test vouchers reversed).

| Run | Post journal / voucher | Reversal journal / voucher | Net |
| --- | --- | --- | --- |
| Authoring | `LEDJ-000001` / VVCH-000001 | `LEDJ-000006` / VVCH-000006 | zero |
| Re-validation | `LEDJ-000007` | `LEDJ-000008` | zero |



