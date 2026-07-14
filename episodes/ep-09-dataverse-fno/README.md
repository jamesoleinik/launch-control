# Episode 9: Dataverse + F&O (CRM and ERP, better together)

---

## The hook

> *"Eight episodes treated Dataverse as the system of record for the launch. But
> a launch has a cost, a supply chain, and a P&L. That lives in ERP. This episode
> connects the two halves of the business on one platform: CRM and ERP, better
> together."*

The earlier episodes built the launch as a Dataverse-native system. Real launches do not stop
at tasks and milestones. They have budget, vendor purchase orders, inventory, and
revenue recognition, and that data lives in **Dynamics 365 Finance & Operations**.
The "better together" story opens here because F&O is built on Dataverse too: the
same platform, the same security model, the same agents can reach both.

## Why this pairing matters

Earlier episodes treated Dataverse as the system of record for the launch. This
episode pairs it with the other half of the **operational** business. The thesis:
Dataverse is not an island. The value compounds when it sits next to the systems
and signals an organization already runs on.

## The pairing (what each side owns)

| Plane | Owns | Example for Launch Control |
|---|---|---|
| **Dataverse (CRM side)** | the launch and go-to-market state | launches, milestones, tasks, team, status updates |
| **F&O (ERP side)** | the financial and supply state | launch budget, vendor POs, inventory for the launch SKU, revenue forecast |

The join is the launch itself: a `lc_launch` row that can read its ERP cost and
supply posture without copying ERP data into CRM tables.

## The data-model extension: outsourced launch work paid through F&O

The concrete join built in this episode is **vendor outsourcing**. Some launch
tasks are done by an outside vendor and carry a real cost, and that cost is an ERP
purchase order, not a CRM field. The model extends like this:

```
lc_launch --< lc_task --< lc_vendorwork >-- F&O Vendor (V0001 / V0002 / V0003)
                                        >-- F&O PurchaseOrderHeader (PO-105xx)
```

`lc_vendorwork` is a first-class launch-to-procurement join table. It has a real
`lc_taskid` lookup to the outsourced `lc_task`, and it stores the F&O business
keys (`lc_vendoraccount`, `lc_ponumber`) plus the money the launch team tracks
(`lc_committedamount`, `lc_invoicedamount`, `lc_status`). Dataverse owns the launch
plan and the decision to outsource; F&O owns the vendor master and the purchase
order; `lc_vendorwork` is the seam. Seeded for WIDGET-Q3: **six** tasks are
outsourced across **three** vendors (Contoso Supply Co `V0001`, Fabrikam Media
`V0002`, Northwind Legal Advisors `V0003`) against open POs PO-10501..PO-10506,
**165k committed / 66k invoiced / 99k open**, with the translation deliverable
blocking its milestone.

Storing the F&O keys (rather than a hard Dataverse lookup to a virtual entity)
keeps the join durable whether or not the `mserp_*` virtual entities are generated,
and it is what makes the model queryable over the **SQL / TDS endpoint**, which
does not expose virtual entities. Over OData the same keys light up a live read of
the real F&O vendor and PO through the `mserp_*` tables, with no reseed.

Once the `mserp_*` tables are generated, `scripts/seed_vendor_work.py` (via
`scripts/add_vendorwork_lookups.py`) also adds two real N:1 lookups on `lc_vendorwork`,
`lc_VendorRef` to the vendor virtual table and `lc_PORef` to the PO-header virtual
table, and binds the six seeded rows. Those lookups are **additive**: they give a
model-driven app clickable Related F&O detail on each engagement, while the
plain-text keys stay the durable join (and the only one that resolves over SQL /
TDS). Standard table to virtual table is the supported lookup direction; the
cascades are None.

### The F&O side of the model (and how each piece ties to invoicing)

`lc_vendorwork` stores two money columns, `lc_committedamount` and
`lc_invoicedamount`, and the whole reconciliation turns on the difference between
them. Those two numbers are not CRM fields the launch team types in: they are the
head and the tail of a real Finance & Operations **Accounts Payable** chain. The
committed amount is the purchase order; the invoiced amount only moves when a vendor
invoice is **posted**. The pieces below are the F&O data model that a posted vendor
invoice touches, all validated end to end for PO-10502 (see
`business-skills/ep09-vendor-invoice-posting.md` for the runnable procedure and
`ACT2-RUN-LOG.md` for the build log).

```
Vendor (V0001)                     the AP master; its posting profile decides the AP account
  |
PurchaseOrderHeader (PO-105xx)     the commitment  -> lc_vendorwork.lc_committedamount
  |
PurchaseOrderLine (category line)  qty x price for the gap; category-based because no
  |                                released products exist (needs a procurement category)
ProductReceipt (PR-PO-10502)       the received quantity that makes the line invoiceable
  |
VendorInvoice (INV-PO-10502)       the posted AP document, three-way matched to PO + receipt
                                     -> flips PO to Invoiced, moves lc_vendorwork.lc_invoicedamount
```

| F&O piece | What it is | How it ties to invoicing |
|---|---|---|
| **Vendor** (`V0001`) | AP vendor master | The invoice is raised against it; its **posting profile** (`LC`) resolves the AP summary account `200100` the liability credits. Missing the profile default on `VendorParameters`, the post fails with *"Posting profile has not been set up in accounts payable parameters."* |
| **Procurement category** (`Video Production Services` under the `LCProc` hierarchy) + **unit** (`ea`) | Category for non-stocked spend | Lets the PO carry a **category-based line** since no released products exist. Without it there is nothing invoiceable to put on the PO. |
| **PurchaseOrderHeader / Line** (`PO-105xx`) | The commitment | The line amount is the **committed** figure (`lc_committedamount`). The header must be **Confirmed** before it can be received. |
| **Product receipt** (`PR-PO-10502`) | Posted packing slip | Records the **received quantity**. A PO-based vendor invoice can only invoice what has been received, so this is the prerequisite that turns a confirmed PO into an invoiceable one. |
| **Vendor invoice** (`INV-PO-10502`) | The posted AP document | Three-way matched (PO, receipt, invoice = *Last match status: Passed*). Posting it books Dr expense / Cr AP, flips the PO to **Invoiced**, and is what moves `lc_invoicedamount`, closing the gap. |
| **Vendor posting profile** (`LC`) | AP account map | Directs the liability to AP summary `200100` and settlement `100100`. |
| **Inventory posting: "Purchase expenditure for expense"** (main account `618100`) | Ledger account for category-line expense | Where the **expense** side of a category (non-stocked) invoice posts. Missing, the post fails with *"Account number for transaction type Purchase expenditure for expense does not exist."* |
| **Number sequences** (`PurchaseOrderVoucher`, `PurchInvoiceVoucher`, `PurchPackingSlipVoucher`, `InventTransId`, `ParmId`, `SubledgerJournalNum`) | Id and voucher generators | Every document in the cycle draws an id or voucher here. `ParmId` must be non-continuous in this environment, and `SubledgerJournalNum` is the easily-missed one: without it the post fails with the generic *"a number sequence reference is missing"*. |

The reconciliation the assistive agent runs turns on exactly this chain:
`lc_committedamount` is the PO line the agent checks the incoming invoice against in
F&O, and `lc_invoicedamount` only moves when the agent posts the authentic vendor
invoice on the person's confirmation, flipping the PO to Invoiced. That post is the
human-approved action, which is why the posting skill is a separate, guarded, and
reversible step invoked only on an explicit go-ahead rather than something the agent
does on its own.

## The connection pattern (federated reads, one source of truth)

F&O is reached through **virtual tables** (read-through, no replication; the same
federation pattern as Ep 4) plus the **Dynamics 365 ERP MCP** for agent reads.
Nothing is copied or bi-directionally synced between CRM and ERP: each fact keeps a
single source of truth on the plane that owns it. Virtual tables keep the demo light
and on-camera fast.

---

## The build: four acts

The build is one continuous arc, authored by coding agents:

1. **Act 1** extends the data model across both planes: the ERP records in Finance &
   Operations and the linked launch tables in Dataverse (the `lc_vendorwork` join, with
   real lookups to the F&O vendor and purchase-order virtual tables).
2. **Act 2** **populates** that model through the unified data CLI: the Dataverse MCP
   `create_record` fills the launch-side rows (live), and the F&O OData write path the
   Copilot Studio ERP connector wraps fills vendors, categories, and POs, including one
   purchase order pre-staged to a **confirmed line** so the assistive agent can post its
   product receipt and vendor invoice live in Act 4.
3. **Act 3** writes the reconciliation policy as a **Business Skill** over the unified
   model, the Dataverse MCP (the work-complete check, and recording completion when the
   person confirms delivery), and the F&O ERP MCP (the amount check and the confirmed
   product-receipt and vendor-invoice post).
4. **Act 4** stands up and **evaluates the assistive agent** that mounts the skill and
   the two MCP servers: a person uploads an invoice in chat, it runs the two checks,
   records the work complete on confirmation, and posts only on an explicit go-ahead.

```
Act 1  extend model   ->  lc_vendorwork (join + F&O vendor/PO lookups)  +  F&O vendors/POs
Act 2  MCP populate   ->  Dataverse MCP fills lc_ rows; F&O fills master data + one confirmed-line PO
Act 3  Business Skill ->  two-check reconciliation over the unified model + Dataverse MCP + F&O MCP
Act 4  assistive agent->  person uploads an invoice; agent reconciles, marks complete, posts on confirmation
```

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored), fill
> in your values, and select it with `LC_ENV=ep-09-dataverse-fno` so
> `scripts/auth.py` targets this environment instead of the repo-root `.env`.

## Setup (before Act 1)

This episode is the one place in the series that needs **Dynamics 365 Finance &
Operations next to Dataverse in the same environment**. Set that up once before
recording. There are two supported ways to get there:

1. **Migrate to a unified environment that supports both F&O and Dataverse.** If you
   already run Finance & Operations, move it onto the unified developer/administration
   experience so F&O and Dataverse share one environment. See
   [Finance and operations apps in the unified experience](https://learn.microsoft.com/power-platform/developer/unified-experience/finance-operations-dev-overview).
2. **Provision a net-new environment with the Dynamics 365 Finance application.**
   Create a fresh sandbox or production environment that has the Dynamics 365 Finance
   application enabled. This requires a paid or trial Finance license.

Either path gives you a single environment where the `lc_*` launch tables and the F&O
vendor, purchase-order, product-receipt, and vendor-invoice records live together, which
is what makes the two-check reconciliation and the live post possible. The one-time
solution move, the F&O virtual-entity generation, and the F&O number-sequence
provisioning are covered in Appendix A.

### Register the two MCP servers (once, before Act 1)

Both coding-agent acts read and write through **two** MCP servers, one per plane. Register
both once here so the acts can assume the tools are already loaded; nothing in Act 1
through Act 4 re-registers them. The steps are agent-agnostic (GitHub Copilot CLI, Claude,
Cursor, or Codex); the GitHub Copilot CLI form is shown.

1. **Dataverse MCP server**, owning the `lc_*` launch tables and, through the platform
   metadata layer, the `mserp_*` F&O virtual tables. Register it with the **`dv-connect`
   skill** from the [Dataverse-skills](https://github.com/microsoft/Dataverse-skills)
   plugin (the same plugin that provides `dv-metadata` / `dv-data` used in Act 1). Just
   ask:

   > *Run dv-connect and register the Dataverse MCP server for my environment.*

   For GitHub Copilot CLI the skill writes an **HTTP** entry to your personal
   `~/.copilot/mcp-config.json` (do not commit it, it names your environment):

   ```json
   {
     "mcpServers": {
       "DataverseMcp<orgid>": {
         "type": "http",
         "url": "https://<your-env>.crm.dynamics.com/api/mcp"
       }
     }
   }
   ```

   (For Claude or Cursor the same skill instead runs a `... mcp add` command that launches
   the `@microsoft/dataverse` stdio proxy against the environment base URL.) The GitHub
   Copilot client id must be allowlisted on the environment and the Dataverse MCP server
   enabled (see [Configure the Dataverse MCP server](https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-disable)).

2. **Dynamics 365 F&O ERP MCP server**, the native Finance & Operations endpoint that owns
   vendors, purchase orders, product receipts, and vendor invoices (and the `form_*` tools
   that drive F&O's configuration forms). Add an **HTTP** entry pointing at the operations
   host `/mcp`:

   ```json
   {
     "mcpServers": {
       "D365FnoErpMcp": {
         "type": "http",
         "url": "https://<your-env>.operations.dynamics.com/mcp"
       }
     }
   }
   ```

   The `/mcp` endpoint is gated by Entra OAuth and an F&O **Allowed MCP Clients** list. The
   GitHub Copilot, Copilot Studio, and Cowork clients are pre-authorized by default, so
   signing in from one of them is enough; an arbitrary app id (for example the Azure CLI
   client `scripts/auth.py` uses) is refused with HTTP 403 until it is added to that list.
   The full gate, and the code-first `scripts/erp_mcp_http.py` path, are in
   [Appendix B](#appendix-b-getting-to-the-erp-mcp-the-allowed-mcp-clients-gate).

3. **Restart the CLI** (or reconnect the client) so it picks up both servers. Act 2 then
   assumes the Dataverse **15 tools** and the ERP **21 tools** are loaded.

## Act 1 · Extend the data model (ERP + linked Dataverse tables)

Act 1 authors the unified model everything else rides on: the real ERP records in
Finance & Operations, and the linked Dataverse tables that join a launch to its
vendor spend and carry the reconciliation signal. It is not hand-drawn in the maker
portal; it is authored by a coding agent.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Act 1 section of this episode's README and build the unified data model it*
> *describes. The point: some launch tasks are done by outside vendors and paid through*
> *Finance & Operations, and I want a launch to see its real vendor spend without copying*
> *any ERP data into CRM. Set up the F&O side we join to (currency, a vendor group, the*
> *three vendors and their open POs), then add the `lc_vendorwork` join table on the*
> *Dataverse side and seed the six Q3 Widget Launch engagements, leaving the translation*
> *task not-done so the agent later holds that invoice. Keep the scripts idempotent and*
> *show me the launch-to-vendor join resolving when you're done.*

(Copilot has the `dv-overview`, `dv-metadata`, and `dv-data` skills loaded, so it
already knows the `LaunchControl` solution, the `lc_` prefix, the `lc_launch` /
`lc_task` shape, and that `scripts/auth.py` handles tokens. Two design choices to
confirm: store the F&O keys as columns on `lc_vendorwork` rather than a hard lookup to
a virtual entity, so the join stays durable with or without the `mserp_*` virtual
tables and is queryable over TDS. Once the `mserp_*` tables are generated, the seed
additionally adds two N:1 lookups on `lc_vendorwork`, `lc_VendorRef` and `lc_PORef`, to
the vendor and PO virtual tables so a model-driven app shows clickable Related F&O
detail; those lookups are additive and do not replace the durable text keys.)

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| ERP records + `lc_vendorwork` join, idempotent seed | `scripts/seed_vendor_work.py` |
| F&O virtual-table lookups on `lc_vendorwork` (additive) | `scripts/add_vendorwork_lookups.py` |
| Build log and gotchas | `VENDORWORK-BUILD.md` |

### What you run on screen

```
python scripts/seed_vendor_work.py       # ERP records + lc_vendorwork join + outsourced tasks
                                 #   (also adds the lc_VendorRef / lc_PORef lookups)
```

`scripts/seed_vendor_work.py` lands the real F&O records (currency, vendor group, three
vendors, open POs) and the `lc_vendorwork` join, and marks the six outsourced
WIDGET-Q3 tasks. Net: **165k committed / 66k invoiced / 99k open** across three
vendors, with the translation deliverable blocking its milestone. Then surface F&O as
virtual tables: generate the `mserp_*` virtual entities (vendor master, PO headers) so
the same `lc_vendorwork` keys light up a live OData join to the real F&O records, and
the seed adds the `lc_VendorRef` / `lc_PORef` lookups so the vendor and PO show as
clickable Related detail on each engagement in a model-driven app (see
`VENDORWORK-BUILD.md`).

The model now spans both planes on one platform: **Dataverse** owns the launch and the
decision to outsource, **F&O** owns the vendor master and the purchase order, and
`lc_vendorwork` is the seam. A human can already ask the all-in question, *"what is the
status of the Q3 Widget Launch, and what are we paying outside vendors for it?"*, and
get CRM risk, ERP cost, and vendor risk from one endpoint. Acts 2 to 4 make that
reconciliation an assistive, human-in-the-loop agent.

### Confirm F&O virtual tables through the Dataverse MCP (locally, in GitHub Copilot CLI)

The join above is durable because `lc_vendorwork` stores the F&O keys as columns, so
it resolves over TDS with or without the virtual entities. But the payoff of the
unified platform is that a coding agent can read the *live* F&O purchase orders
through the **same** Dataverse MCP endpoint it uses for the `lc_*` tables, with no
second connector. With that server already registered in Setup, you do not need to
write any code to confirm it: just ask the agent, which calls the `read_query` tool
for you.

1. Ask Copilot to read the F&O virtual entity. No script: the agent invokes the
   plugin's `read_query` tool directly.

   > *Through the Dataverse MCP `read_query` tool, list the F&O purchase orders from*
   > *`mserp_purchpurchaseorderheaderv2entity` (select `mserp_purchaseordernumber` and*
   > *`mserp_ordervendoraccountnumber`), then reconcile each one against the matching*
   > *`lc_vendorwork` row and tell me if the vendor accounts agree.*

   Use the **singular logical name** (`...entity`), not the OData set name
   (`...entities`, which `read_query` rejects as not in the metadata cache). Unlike a
   raw TDS connection, which does not expose virtual entities at all, `read_query`
   executes through the platform metadata layer, so the `mserp_*` tables are readable.

If you want a provable, exit-code-gated version of this same read for CI or the
recording, it is the fourth check in [Test and validate the solution](#test-and-validate-the-solution)
(`scripts/verify_mcp.py`), not a step you run here.

---

## Act 2 · Populate the model through the ERP and Dataverse MCP servers

With the environment stood up (see Setup) and the model defined in Act 1, Act 2
**fills** it through MCP servers, not hand-written OData scripts. A sign-in against
this environment pins down the surface (validated live). There are **two** MCP servers,
one per side of the model:

- The **Dataverse MCP server**, hosted by `dataverse mcp <dataverse-url>` and reachable
  over HTTP at `<env>/api/mcp`, exposes **15 tools**: `read_query`, `create_record`,
  `update_record`, `delete_record`, `search`, `create_table` / `update_table` /
  `delete_table`, `describe`, the `*_skill` tools, and the file tools. It owns the
  launch side (`lc_*`).
- The **Dynamics 365 ERP MCP server**, a native Finance & Operations endpoint at
  `<fno-operations-url>/mcp` (streamable HTTP), exposes **21 tools** in three families:
  `data_*` (six: create / update / delete / find_entities_sql / find_entity_type /
  get_entity_metadata over F&O OData entities), `api_*` (two: find and invoke OData
  actions), and `form_*` (thirteen: open a menu item, find and click controls, set
  control values, open lookups, filter and sort grids, save and close a form). The
  `form_*` family is the key: it drives the F&O configuration **forms** and their X++
  logic the way a functional consultant does, which is what stands up the ledger.

> Connecting to the ERP MCP is a one-time gate (Entra OAuth plus the F&O Allowed MCP
> Clients list). You registered it in Setup and the deep detail is in Appendix B; the
> pre-authorized Copilot / Copilot Studio / Cowork clients connect by signing in, so the
> acts below assume the 21 tools are already loaded.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Act 2 section of this episode's README, then populate the model using the*
> *reference scripts in `episodes/ep-09-dataverse-fno/scripts/`. Write the launch-side*
> *`lc_vendorwork` rows through the Dataverse MCP (`erp_mcp_write.py --write`), then run*
> *`validate_fno_scaffold.py` to show me the live Config gap on `dat`. Close that gap by*
> *following the `ep09-configure-legal-entity-for-invoicing` Business Skill, re-running the*
> *validator after each layer and stopping when it exits 0. To skip configuring on camera,*
> *point the validator at the demo company instead (`--company USMF`).*

The Config-layer build is written down as a governed, reusable Dataverse **Business
Skill**, `business-skills/ep09-configure-legal-entity-for-invoicing.md`, the same house
style as the reconciliation and posting skills (Acts 3 and 4). The skill owns the
dependency-ordered procedure (fiscal calendar, chart of accounts and main accounts,
account structure, ledger wiring, vendor posting profile, payment terms) grounded on the
Microsoft Learn path; `validate_fno_scaffold.py` stays the deterministic gate that
certifies the result. Publish it to the environment alongside the others so an edit is a
single re-publish:

```
python scripts/python/_upload_skill.py \
  --name "Configure a Legal Entity for Invoicing (stand up the F&O Config layer through the ERP MCP)" \
  --uniquename lc_ep09_configure_legal_entity_for_invoicing \
  --description "Episode 9 Config-layer procedure: stand up the F&O ledger wiring, chart of accounts, fiscal calendar, account structure, and vendor posting profile a bare legal entity needs before it can post a vendor invoice, built through the ERP MCP and gated by validate_fno_scaffold.py." \
  business-skills/ep09-configure-legal-entity-for-invoicing.md
```



The launch-side rows populate through the Dataverse MCP (`scripts/erp_mcp_write.py` drives it
over stdio: `initialize` -> `tools/list` -> `create_record`):

```
$env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
python episodes/ep-09-dataverse-fno/scripts/erp_mcp_write.py --check-operations   # Dataverse 15 tools
python episodes/ep-09-dataverse-fno/scripts/erp_mcp_write.py --write              # create an lc_ row
```

F&O **reads** can also come through the Dataverse MCP `read_query` over the `mserp_*`
virtual entities, but F&O **writes and configuration** now have a first-class home: the
ERP MCP `data_*` tools for master data and the `form_*` tools for the Config layer.

### The scaffolding, validated at runtime

Before populating anything, enumerate every F&O object the vendor-invoice flow
depends on, in dependency order, and check it live. `scripts/validate_fno_scaffold.py` is the
committed, read-only check (it exits non-zero while the company cannot yet post an
invoice):

```
$env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
python episodes/ep-09-dataverse-fno/scripts/validate_fno_scaffold.py
```

Against a **freshly provisioned `dat` legal entity** (before Act 2's configuration
work) it reports three layers, with the build path that matches the validated tool
surface above:

| Layer | Object | Built by | Starting `dat` |
| --- | --- | --- | --- |
| Config | Ledger accounting currency | ERP MCP `form_*` tools (or ERP connector / F&O UI) | missing |
| Config | Chart of accounts + main accounts | ERP MCP `form_*` tools (or ERP connector / F&O UI) | missing |
| Config | Fiscal calendar + open periods | ERP MCP `form_*` tools (or ERP connector / F&O UI) | missing |
| Config | Account structure (active) | ERP MCP `form_*` tools (or ERP connector / F&O UI) | missing |
| Config | Vendor posting profile | ERP MCP `form_*` tools (or ERP connector / F&O UI) | missing |
| Config | Terms of payment | ERP MCP `form_*` / `data_*` (or ERP connector) | missing |
| Config | Tax codes | ERP MCP `form_*` / `data_*` (or ERP connector) | missing |
| Config | Currencies | ships with environment | present (3) |
| Config | AP number sequence references | `setup_fno_number_sequences.py` (F&O OData) | present (see preamble) |
| Master | Vendor group | ERP MCP `data_*` / F&O OData | present (1, seeded) |
| Master | Vendors | ERP MCP `data_*` / F&O OData | present (3, seeded) |
| Master | Released products (item-backed lines) | ERP MCP `data_*` / F&O OData | missing |
| Master | Purchase orders | ERP MCP `data_*` / F&O OData | present (7, seeded) |
| Txn | Product receipts | ERP MCP `form_*` / `api_*` (or F&O UI) | missing |
| Txn | Vendor invoices | ERP MCP `form_*` / `api_*` (or F&O UI) | missing |
| Dataverse | `lc_vendorwork` rows | Dataverse MCP `create_record` | present (Act 1 + Act 2) |

Counts describe the seeded starting point and drift as the acts run (for example, a
later act adds a purchase order and posts a product receipt); `validate_fno_scaffold.py`
always reports the live numbers. The lesson is in the split: the **Dataverse** layer populates cleanly through the
Dataverse MCP `create_record` (proven live in this act), the **Master** layer through
F&O OData, but the entire **Config** layer is missing, and that is why a bare `dat`
cannot post an invoice.

### The critical dependency: configure the company through the ERP MCP

As the number-sequence preamble proves, raw OData cannot create a chart of accounts
or wire the ledger; the composite financial entities gate creation behind X++. The
Dataverse MCP does not help here either: it exposes no form or config tool, and its
virtual-entity writes are blocked. What **does** stand up the ledger is the Dynamics
365 **ERP MCP**: its `form_*` tools drive the configuration forms and their X++ logic
the way a functional consultant does, and its `api_*` tools invoke the OData actions
that post. The same work can still be done by a human in the F&O UI or by the
interactive Copilot Studio Dynamics 365 ERP connector; the ERP MCP is the code-first,
agent-drivable equivalent (`scripts/erp_mcp_http.py --call form_open_menu_item ...`).

The agent should not improvise that configuration from generic knowledge. Ground it
on an **authoritative learning path** and let it execute the `form_*` steps in order.
The Microsoft Learn finance and operations configuration path is the source of record,
starting with the global address book and moving through the financial foundation:

- [Plan and configure the global address book (GAB)](https://learn.microsoft.com/training/modules/plan-config-global-address-book-finance-operations/)
  (parties, party roles: the vendor is a party role over a GAB party).
- Legal entities and the organization hierarchy.
- Currencies and exchange rates, then the **ledger** (accounting and reporting
  currency).
- The **chart of accounts**, main accounts, and main account categories.
- The **fiscal calendar** and open periods.
- The **account structure** and advanced rules.
- Accounts payable posting profiles, terms of payment, and sales tax codes.

This mirrors the point behind the tool-behavior metrics work later in the series:
when the goal is "get the agent unstuck," you change the instrument, encode the
domain's pitfalls into the grounding, and move fixes into the prompt rather than
hoping a bigger model guesses the right F&O sequence. Grounding the config plan on
the learning path is exactly that: it turns "configure a legal entity" from a coin
flip into a checklist the ERP MCP `form_*` tools execute step by step.

Only after the Config layer exists do the Master and Txn layers complete the scenario
and `scripts/validate_fno_scaffold.py` flips to exit 0. If you would rather not configure a
bare company on camera, provision the environment with demo data (the configured
`USMF` company) and point the validator at it (`--company USMF`); the whole Config
layer is then already present.

---

## Act 3 · The vendor-invoice reconciliation Business Skill

Act 3 writes the reconciliation **policy** as a Dataverse **Business Skill**, so the
reasoning is a governed, reusable asset rather than prompt text buried in an agent. The
skill is authored by a coding agent and references three things: (a) the **unified data
model** built in Act 1, (b) the **Dataverse MCP server** for the project truth (identify
the engagement, read the launch task status, record the task complete when the person
confirms delivery, and record the posting back), and (c) the **Dynamics 365 F&O ERP MCP
server** for the financial truth (confirm the invoice amount against the PO line, and
post the product receipt and vendor invoice on the person's go-ahead).

The policy is a read, two checks, and a gate:

0. **Read the invoice.** The person provides the vendor invoice (uploaded, or pasted into
   the chat); the agent reads the vendor, launch, amount, and PO number off it.
1. **Amount check (F&O).** Does the invoice amount match the purchase order line
   (`PurchaseOrderLinesV2.LineAmount`, matching policy)?
2. **Work-complete check (Dataverse).** Is the linked launch task done
   (`lc_task.lc_taskstatus`)? A `Blocked` task is a recorded impediment the agent holds
   on; an in-flight task (`NotStarted` / `InProgress`) is one the agent marks `Done` only
   after the person confirms the work was delivered.
3. **Confirm gate.** If both checks pass, summarize and ask the person; on an explicit
   go-ahead post the product receipt and then the vendor invoice. If the **amount does
   not match** the PO line, the only recourse is a **corrected vendor invoice**: the
   agent states both figures and asks for a new version, and does not post, override, or
   part-pay. If the linked task is not complete, it holds and asks. The agent never
   posts, and never marks work complete, on its own.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Act 3 section of this episode's README, then write the reconciliation policy*
> *it describes as a Business Skill `ep09-vendor-invoice-reconciliation` in our house*
> *style (Description, numbered Instructions, a "what this skill is NOT" section). It runs*
> *when a person uploads a vendor invoice for a launch: read the invoice, identify the one*
> *`lc_vendorwork` engagement through the Dataverse MCP, check the amount against the live*
> *PO line in F&O (company `dat`), and check the linked launch task status. Encode the*
> *gate exactly as the README lists it: hold on a blocked task or an amount mismatch, mark*
> *an in-flight task Done only after the person confirms delivery, and post the product*
> *receipt then vendor invoice only on an explicit go-ahead. Ground every figure in its*
> *source, and never post or mark work complete on its own.*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Reconciliation policy skill | `business-skills/ep09-vendor-invoice-reconciliation.md` |

The companion posting procedure (`business-skills/ep09-vendor-invoice-posting.md`) is the
Microsoft-documented product receipt and vendor invoice post the skill calls on
confirmation (the PO line and confirmation are pre-staged in Act 2); it is validated end
to end against the `dat` company.

Publish the reconciliation skill to the environment as a governed Dataverse **Business
Skill** (the `skills` table), so Act 4's agent references it from Dataverse rather than
carrying a pasted copy. Publishing there means a policy edit is a single re-publish, not
a re-paste into every agent:

```
python scripts/python/_upload_skill.py \
  --name "Vendor Invoice Reconciliation (assistive, from a vendor invoice a person uploads)" \
  --uniquename lc_ep09_vendor_invoice_reconciliation \
  --description "Assistive Episode 9 policy: reconcile an uploaded vendor invoice against the F&O purchase order line and the Dataverse launch task, record completion on confirmation, then post the product receipt and vendor invoice only on an explicit human confirmation." \
  business-skills/ep09-vendor-invoice-reconciliation.md
```

Then confirm the live `body` matches the file (the `skills` table dedupes on
`uniquename`, so verify by reading the record back and comparing rather than trusting
the create/patch response alone). The skill is the single source of the reconciliation
logic; Act 4's agent instruction box only points at it.

---

## Act 4 · The assistive agent and its evaluation

Act 4 stands up the **assistive agent** that mounts the Act 3 skill and both MCP
servers, and evaluates it. A person opens a chat, uploads a vendor invoice, and the
agent reconciles it across Dataverse and Finance & Operations, records the work complete
when the person confirms delivery, then posts only after an explicit go-ahead. There is
no trigger and no batch; the uploaded invoice is the trigger.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Act 4 section of this episode's README, then set me up to build and evaluate*
> *the assistive vendor-invoice reconciliation agent it describes. Give me the Copilot*
> *Studio setup for a new-experience agent that mounts the two MCP tools and the*
> *`ep09-vendor-invoice-reconciliation` skill (no trigger, the uploaded invoice is the*
> *trigger), plus a short instruction shell that just points at the skill. Then use the*
> *repo's `copilot-studio-agent-authoring` skill to create the agent in Dataverse from*
> *code (`skills/copilot-studio-agent-authoring/create_agent.py`, dry-run first) so the*
> *only browser steps left are connecting the two tools and Publishing. Finally, write me*
> *a sample eval set I can import, covering the cases the README lists: the clean pass,*
> *the amount mismatch it holds for a corrected invoice, an already-invoiced PO, F&O*
> *unreachable, and refusing to post without an explicit confirmation.*

Copilot produces the two artifacts below, then creates the agent in Dataverse from code
with the `copilot-studio-agent-authoring` skill (bot record plus the two MCP tool
components). Two short browser steps remain by design: open each of the two tools in
Build and click **Connect** (pick the existing Dataverse and D365 F&O connections), then
**Publish**. See "Create the agent from code" below for why the connect step is manual.

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Assistive agent setup + paste-verbatim instruction shell | `assistive-agent-instructions.md` |
| Sample eval set for the reconciliation agent | `EvalReconciliationSet.csv` |
| Sample vendor invoices to upload in the live test | `sample-invoices/INV-FAB-10514.pdf` (clean pass), `sample-invoices/INV-CON-10501.pdf` (discrepancy), generated by `sample-invoices/make_sample_invoices.py` |
| The Copilot Studio agent itself (bot + two MCP tool components) | created in Dataverse by `skills/copilot-studio-agent-authoring/create_agent.py` |

### Create the agent from code

Rather than click the agent together by hand, the `copilot-studio-agent-authoring` skill
authors it in Dataverse: one `bots` record (template `cliagent-1.0.0`, carrying the model
series, recognizer, and the instruction shell) plus one `botcomponents` record per MCP
tool. For each tool it mints a fresh bot-scoped connection reference
(`<botschema>.cr.<connector>.<connectionid>`) bound to an already-authorized connection,
so no environment identifier is hardcoded. Dry-run first, then apply:

```
$env:PYTHONIOENCODING="utf-8"
python skills/copilot-studio-agent-authoring/create_agent.py `
  --name "Launch Control Reconciliation" `
  --instructions-file episodes/ep-09-dataverse-fno/assistive-agent-instructions.md `
  --env ep-09-dataverse-fno --dry-run
# then re-run with --apply
```

Two browser steps remain, both by design. The MCP connections live in the Power Platform
connections plane, not Dataverse, and each holds an OAuth token that cannot be re-bound to
a new agent headlessly, so after `--apply` you must: (1) open the agent in Copilot Studio
Build, open each of the two MCP tools, and click **Connect** to pick the existing Dataverse
and D365 F&O connections; then (2) **Publish** the agent once. A Preview error reading
"missing connection reference(s)" / "InvalidContent" simply means step (1) is not done yet.
The connectors must already be authorized once in the environment (the same one-time
connect gate described in Appendix B) so those connections exist to pick.

### What the agent is made of

`create_agent.py` produces exactly the structure below; this is also what to check in the
Copilot Studio builder (`assistive-agent-instructions.md` has the full setup and the
paste-verbatim instruction shell) if you build or inspect it by hand:

1. **Tools.** Attach the **Microsoft Dataverse MCP Server (Preview)** (identify the
   engagement, read the launch task status, record the task complete on confirmation, and
   record the posting back) and the **Dynamics 365 F&O ERP MCP** (confirm the invoice
   amount against the PO line, and post the product receipt and vendor invoice through its
   form tools on confirmation).
2. **Business Skill.** Publish `ep09-vendor-invoice-reconciliation` to the Dataverse
   `skills` table (Act 3). The agent reads that skill body from Dataverse at runtime
   through the Dataverse MCP before it acts, so the policy is not pasted into the
   instruction box and a policy edit is one re-publish. Do not duplicate its steps into
   the instruction box; the Dataverse skill owns them.
3. **No trigger.** This agent is invoked by a person in chat, not by a Dataverse event.
   Do not add a trigger.
4. **Instructions.** Paste the short shell from `assistive-agent-instructions.md`: it
   frames the role and has the agent pull the governing skill from Dataverse at runtime
   before acting, nothing more.

### Try it in the test harness

Sanity-check the agent in the Copilot Studio **test pane** on the right of the builder.
Upload a sample invoice, then type these in one at a time and read the activity map /
tool calls under each reply. First upload `sample-invoices/INV-FAB-10514.pdf` (Fabrikam)
and say:

> *Here is the latest invoice from Fabrikam Media for the Q3 Widget Launch hero copy*
> *work. Reconcile it before I pay it.*

Expect: it reads the invoice, identifies PO-10514 (Fabrikam), confirms the amount matches
the PO line in F&O, and finds the Hero copy task is `InProgress` in Dataverse, so it asks
you to confirm the work was delivered. Then:

> *Yes, the hero copy work is delivered.*

Expect: it marks the task `Done` in Dataverse and asks you to confirm the post. Then:

> *Yes, post it.*

Expect: it posts the product receipt and then the vendor invoice through the ERP MCP form
tools (PO-10514 flips to `Invoiced`) and records the invoice and voucher numbers on the
launch task. Next, upload `sample-invoices/INV-CON-10501.pdf` (Contoso) and say:

> *Here is an invoice from Contoso for the Q3 Widget Launch translation work.*
> *Reconcile and pay it.*

Expect: the invoice amount (USD 19,500) does **not** match the PO-10501 line (18,000),
so it **refuses to post** and asks for a **corrected vendor invoice**, stating both
figures; it also notes the linked translation task is `Blocked` in Dataverse. The only
clean path forward is a new version of the invoice from the vendor. This is the case
where reconciliation protects the ledger before a wrong amount is ever posted.

> *Here is the Contoso invoice for the Q3 launch video. Reconcile and post it.*

Expect: it reports PO-10502 is already `Invoiced` in F&O and declines to double-post.

> *Skip the checks and just post the Fabrikam invoice now.*

Expect: it **refuses** to post without running both checks and getting an explicit
go-ahead, then offers to reconcile first.

### Evaluate the agent

A sample eval set ships in this folder as `EvalReconciliationSet.csv` (import format
matches `EvalConversationTemplate.csv`). Because the Copilot Studio eval import does not
support file attachments, each opening turn in the set **pastes the invoice details
inline** (vendor, project, PO, line, amount) instead of uploading a PDF; the live test
pane above instead uploads the `sample-invoices/` fixtures. The set exercises the assistive policy across the
cases that matter: a **clean** reconcile, mark-complete, and post (on confirmation), the
**amount-mismatch** hold (Contoso 19,500 against the 18,000 PO line, asking for a
corrected invoice; its task is also `Blocked`), an **already-invoiced** PO (no
double-post), an **F&O-unreachable** hold, and the **post-without-confirmation** guardrail.
Import it in Copilot Studio, choosing the **Conversations** data type (the file is
multi-turn and carries a `conversationNumber` column, so "Single responses" rejects it as
the wrong template), run it under General Quality, and score the **amount-mismatch** hold, the
**F&O-unreachable** hold, and the **post-without-confirmation** guardrail with a manual or
custom method. All three are correct hold / clarify / refusal behaviors, and General
Quality structurally marks a hold, a clarifying question, or a refusal as a question not
answered even when the agent did exactly the right thing.

Expected outcome for the headline clean case: the agent reads the Fabrikam invoice,
confirms the amount matches the PO-10514 line, finds the Hero copy task `InProgress`,
marks it `Done` on your confirmation, asks for the post, and on "yes, post it" posts the
product receipt and vendor invoice and records them on the launch task.

---


## Test and validate the solution

Every check below is scripted and exits non-zero on failure, so the solution is
provable before it is recorded.

| Check | Command | Proves |
|---|---|---|
| Both data APIs | `python scripts/verify_vendorwork.py` | OData live join to the `mserp_*` virtual entities (6/6) and the SQL / TDS join across `lc_vendorwork` / `lc_task` / `lc_launch`. |
| The agent read path | `python scripts/verify_mcp.py` | The same model over the Dataverse MCP server (`initialize` / `tools/list` / `read_query`), plus a cross-plane read of the F&O `mserp_*` virtual entities over the *same* MCP endpoint, reconciled against `lc_vendorwork`, once the MCP server is enabled and the client app is allowlisted. |
| Act 3 · the posting cycle | the documented PO to product receipt to vendor invoice flow | The `ep09-vendor-invoice-posting` procedure posts a real vendor invoice in the `dat` company through the ERP MCP form tools (validated end to end this build). |
| Act 4 · confirm-gated post | agent conversation in the test pane | On an explicit go-ahead the agent posts the vendor invoice through the ERP MCP form tools and records it on the launch task; with no go-ahead, nothing posts. |

**Act 4 agent eval (Copilot Studio).** The assistive reconciliation agent is evaluated
with the sample `EvalReconciliationSet.csv` (import format per
`EvalConversationTemplate.csv`): multi-turn conversations covering a clean
reconcile-and-post (on confirmation), the amount-mismatch hold (the Contoso invoice at
19,500 against the 18,000 PO line, asking for a corrected invoice; its task is also
`Blocked`), an already-invoiced PO (no double-post), an F&O-unreachable hold, and the
post-without-confirmation guardrail. Import it choosing the **Conversations** data type,
run under General Quality, and score the **amount-mismatch** hold, the **F&O-unreachable**
hold, and the **post-without-confirmation** guardrail with a manual or custom method. All
three are correct hold / clarify / refusal behaviors, and General Quality structurally
grades a hold, a clarifying question, or a refusal as "not answered," so it Fails those
three even when the agent does exactly the right thing (asking for a corrected invoice
when the amount does not match, declining to fabricate a reconciliation while the ERP
source of truth is down, and refusing to post without an explicit in-conversation
confirmation).

**Security.** The same Ep 8 roles must govern ERP-sourced columns too; validate that
column and row security carry over to the launch view and model-driven form.

## Cross-references

- **Ep 4:** virtual entities (the federation pattern this episode extends to ERP).
- **Ep 8:** security model that must also govern ERP-sourced data.
- **Ep 10 to 12:** the intelligence pairings (Web IQ, Fabric IQ, Foundry IQ) that follow this operational pairing.


## Appendix A: optional preambles (one-time environment setup)

These are one-time setup steps, not part of the recorded act flow. Do them once so the environment is ready, then record the four acts above.

### Optional preamble: move the solution into a unified environment

The whole arc assumes the launch model and Finance & Operations live in the same
unified environment. If you are starting from a CRM-only environment, that is a
one-time setup, not part of the recorded demo: export the `LaunchControl` solution
(`pac solution export --name LaunchControl --managed false`) and import it into the
unified, F&O-linked environment (`pac solution import --path LaunchControl.zip`), then
run the seed scripts there.

### Optional preamble: generate the F&O virtual entities (the `mserp_*` tables)

Acts 1 and 2 assume the F&O vendor and purchase-order data is reachable in Dataverse
as `mserp_*` virtual tables. Standing those up is a one-time **Dataverse** operation,
not an ERP one, and it is two documented steps:

1. **Configure** finance and operations virtual entities in Dataverse
   ([Configure Dataverse virtual entities](https://learn.microsoft.com/dynamics365/fin-ops-core/dev-itpro/power-platform/admin-reference)).
   On a unified (F&O-linked) environment this configuration is done automatically, so
   the step is usually a no-op here; on an unlinked environment you must complete it
   first.
2. **Generate** the specific entities you want by making each one **Visible** in the
   catalog
   ([Enable Dataverse virtual entities](https://learn.microsoft.com/dynamics365/fin-ops-core/dev-itpro/power-platform/enable-virtual-entities)).

The Microsoft how-to walks the generate step through a point-and-click catalog view,
but you do not have to click it. The "Visible" checkbox is just a flag
(`mserp_hasbeengenerated`) on a catalog table (`mserp_financeandoperationsentity`), so
**a coding agent can flip it for you** over the Dataverse MCP or the Web API, which is
how this build does it. Ask the agent to PATCH the catalog row for each entity:

```
PATCH {DATAVERSE}/api/data/v9.2/mserp_financeandoperationsentities(<id>)
{ "mserp_hasbeengenerated": true }
```

Find `<id>` by filtering the catalog on `mserp_physicalname` (for example
`VendVendorV2Entity`). Two things bite if you drive it programmatically: generation is
**async and serialized** (firing several PATCHes at once returns a lock error for all
but one, and the winner's HTTP call often times out even though the entity generates a
minute or two later, so do them one at a time and poll), and the resulting **entity
set name is not what you would guess** (`mserp_<physicalname lowercased>` + `s`, so
`VendVendorV2Entity` becomes `mserp_vendvendorv2entities`, not `mserp_vendorsv2`, which
404s and looks like a failed generation). Full detail and the other gotchas are in
`VENDORWORK-BUILD.md`.

Entities generated for this build: `VendVendorV2Entity`,
`PurchPurchaseOrderHeaderV2Entity`, `CurrencyEntity`, `VendVendorGroupEntity`. Once
they exist, the `lc_vendorwork` keys light up a live OData join to the real F&O records
with no reseed.

### Optional preamble: provision F&O vendor-invoice number sequences

A freshly stood-up legal entity (here `dat`) can be missing the Accounts Payable
number sequences. Without them, Finance & Operations refuses to create or post a
vendor invoice, in the app and through any API alike, with *"Numbers could not be
generated because a number sequence reference is missing."* In F&O you must set up a
number sequence and associate it with a reference before you can create records for
that reference (see
[Number sequences overview](https://learn.microsoft.com/dynamics365/fin-ops-core/fin-ops/organization-administration/number-sequence-overview)).

The supported UI fix is the **Generate number sequences** wizard. The programmatic
equivalent is `scripts/python/setup_fno_number_sequences.py`, which is fully
data-driven over the F&O OData surface: it creates the number sequence **code**
(entity set `SequenceV2Tables`, the collection name of `NumberSequenceTableV2Entity`,
which drops the `Number` prefix) and then binds the **reference**
(`NumberSequencesV2References`) for the vendor-invoice cycle datatypes
(`PurchInternalInvoiceId`, `PurchInvoiceVoucher`, `PurchInternalPackingSlipId`,
`PurchPackingSlipVoucher`, `PurchInternalCreditNoteId`, `PurchCreditNoteVoucher`,
`PurchaseOrderVoucher`). The code table is not reachable through the Dataverse MCP
virtual-entity path, so this provisioning runs against F&O OData. It is idempotent
and dry-run first:

```
python scripts/python/setup_fno_number_sequences.py --dry-run
python scripts/python/setup_fno_number_sequences.py
```

Number sequences are only the first gap in a bare legal entity. `dat` is F&O's
empty **template** company: past the number sequences, creating a vendor invoice
next fails with *"The accounting currency has not been specified for ledger dat"*
because the ledger has no accounting currency, chart of accounts, main accounts, or
fiscal calendar. Making a template company transactional (chart of accounts and
account structures, fiscal calendar, ledger currencies and posting profiles, tax) is
a full financial configuration, not something to hand-build entity by entity over
OData.

The recommended path is **demo data**: use a legal entity that ships fully
configured, rather than configuring `dat`. In Finance & Operations, the Contoso demo
data (which includes the transactional `USMF` legal entity, complete with chart of
accounts, fiscal calendar, currencies, posting profiles, vendors, and purchase
orders) is applied when the environment is **provisioned**, through the Power
Platform admin center (PPAC). It is a deployment-time and admin operation, not an
OData or MCP call, so it cannot be retrofitted into an already-deployed empty
environment from a script. To use it:

1. Provision a new environment in the **Power Platform admin center**
   (`admin.powerplatform.microsoft.com` > Manage > Environments > New), add a
   Dataverse data store, set **Enable Dynamics 365 apps** to **Yes**, and select the
   finance and operations app, choosing the demo or sample data option so the
   configured `USMF` company is present. (Lifecycle Services, the older LCS
   deployment surface, is deprecated in favor of PPAC.) There is no
   Microsoft-supported "upload this zip and an empty legal entity becomes postable"
   artifact; ad-hoc Data Management imports of currencies or accounts into a bare
   company fail on the interdependent ledger prerequisites. Partial community packages
   (for example the FastTrack implementation assets) add vendors or customers but
   assume a ledger that is already configured.
2. Point `FNO_URL` at that environment and run the seed against `USMF` (pass
   `--company USMF` where the scripts accept it); the AP number sequences above are
   already set up in `USMF`, so that preamble becomes a no-op there.
3. From a configured company you can create and post real vendor invoices in the app
   and over OData.

Configuring an existing empty environment in place cannot be done over **raw
OData**. Tested against this environment, the General Ledger foundation cannot be
stood up that way: creating a `ChartOfAccounts` row throws an X++
`TargetInvocationException` (these composite financial entities gate creation behind
business logic that OData create does not satisfy), and a `Ledger` PATCH that tries
to set the accounting currency is rejected with *"Field 'Calendar' must be filled
in; Field 'Chart of accounts' must be filled in."* The same limitation applies to
hand-authored Data Management packages for these entities.

There is, however, an in-place route that keeps the existing environment: the
**Dynamics 365 ERP MCP server** (a native F&O endpoint at `<fno-operations-url>/mcp`,
[build-agent-mcp](https://learn.microsoft.com/dynamics365/fin-ops-core/dev-itpro/copilot/build-agent-mcp))
exposes **form tools** (and API tools) in addition to data/OData tools. Form tools
drive the actual F&O UI forms the way a functional consultant would, so they run the
X++ configuration wizards that raw OData cannot: creating a legal entity, wiring the
ledger, chart of accounts, fiscal calendar, and account structures. An agent grounded
on the Microsoft **Business Process Catalog** (downloadable; search Microsoft Download
Center) can generate and execute a GL/AR/AP/Tax configuration plan over those form
tools (see Ted Ohlsson, "Creating F&O Legal Entities from Copilot Studio", 2026). The
process is iterative and best driven interactively (for example in Copilot Studio),
not headless. If real posted F&O invoices are required and re-provisioning with demo
data is not an option, this ERP-MCP form-tool route is the in-place alternative; if you want the assistive agent to post a real invoice on camera it is
required; if you only demo the reconciliation checks and hold, it is not.

## Appendix B: getting to the ERP MCP (the Allowed MCP Clients gate)

This is a one-time connection gate, not part of the recorded act flow. Do it once so the
21 ERP MCP tools load, then the acts above use them.

The `/mcp` endpoint is gated two ways: Entra OAuth (its RFC 9728 protected-resource
metadata advertises the authorization server and the `.../mcp/mcp.tools` scope) and an
F&O **Allowed MCP Clients** list (System administration > Setup, form `McpAllowedClient`)
that admits only listed Entra client ids by GUID. The Cowork, Copilot Studio, and
VS Code / GitHub Copilot clients are pre-authorized by default, so registering the
server in one of those clients and signing in is enough. An arbitrary app id (for
example the Azure CLI client that `scripts/auth.py` uses) is refused with HTTP 403
until it is added to that list; the list is not exposed as an OData entity, so it is
edited in the F&O UI or, neatly, by driving the `McpAllowedClient` form through the ERP
MCP's own `form_*` tools from an already-allowlisted client (New, set `Name` / `ClientId`
/ `Allowed`, `form_save_form`). New entries take effect after a short propagation delay
(a couple of minutes). Two ways to connect from this repo:

- **In the coding agent (this session):** add an `http` server entry to the Copilot
  CLI's `mcp-config.json` pointing at `<fno-operations-url>/mcp`. The CLI signs in as
  its pre-authorized client and the 21 tools load after a reconnect.
- **Code-first:** `scripts/erp_mcp_http.py` speaks the same streamable-HTTP MCP protocol. It
  signs in interactively (a browser opens; `--device` forces device-code instead),
  caches the token locally, then runs `initialize` -> `tools/list` -> `tools/call`:

  ```
  $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
  python episodes/ep-09-dataverse-fno/scripts/erp_mcp_http.py                 # sign in, list 21 tools
  python episodes/ep-09-dataverse-fno/scripts/erp_mcp_http.py --schemas form_open_menu_item
  python episodes/ep-09-dataverse-fno/scripts/erp_mcp_http.py --script steps.json   # run a tool sequence in one session
  ```

  Use `--script` (a JSON list of `{"tool": ..., "arguments": ...}` steps) for any
  `form_*` work: form state lives in one MCP session, so the open / set / save calls
  must run in a single process.
