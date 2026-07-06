# Episode 9: Dataverse + F&O (CRM and ERP, better together)

**Status:** ✍️ Draft (Season 2 opener) · 🎬 Not yet recorded
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Dataverse and Dynamics 365 Finance & Operations on one platform · ⭐ Virtual tables + ERP MCP across CRM and ERP (no dual-write) · ⭐ One launch record enriched with ERP cost and supply signal
**Layer:** 🟢 Layer 0 (the data foundation) widening: the source of truth now spans CRM and ERP
**Coding agent:** GitHub Copilot CLI / Copilot Studio (integration authored, not hand-clicked)
**Runtime:** Dataverse + Dynamics 365 Finance & Operations

> **Build status (this pass).** The Dataverse half is **built and seeded** in the
> target environment: the `lc_` launch model (publisher + solution + 5 tables + 10
> lookups) is deployed and the Q3 Widget Launch scenario is seeded (6 milestones,
> 12 tasks with 2 blockers, status updates, team). The agent **Business Skill**
> `lc_ep09erpreadiness` ("Launch ERP Readiness") is created in Dataverse from
> `business-skills/ep09-erp-readiness.md`. The agent shell (Copilot Studio, new
> builder) already has the **Dataverse MCP** and **Dynamics 365 ERP MCP** tools
> attached; paste `agent-instructions.md` (this folder) into its Instructions.
>
> **ERP signals (broad feed, in place now).** A small, clearly labeled table
> `lc_erpsignal` is seeded in the SAME environment (run
> `python seed_erp_signals.py`): three signals for the Q3 Widget Launch (budget
> 575k over a 500k approval, open vendor PO for the CDN appliance, inventory 120 of
> 500 for WIDGET-V1). The agent reads it through the Dataverse MCP. It is the
> narrative signal feed (budget / inventory / PO health) and sits alongside the
> real F&O records below.
>
> **Real F&O records + the launch/procurement join (built, seeded, and verified).**
> Scripted F&O OData writes DO work on this environment (an earlier note that they
> fail at the X++ layer was wrong; a direct per-record OData POST is the reliable
> loader on a bare env). `seed_vendor_work.py` lands the concrete CRM + ERP join:
> it creates real F&O records (currency USD, vendor group `DEMO`, three vendors
> `V0001` Contoso Supply Co / `V0002` Fabrikam Media / `V0003` Northwind Legal
> Advisors, and six open purchase orders PO-10501..PO-10506), then extends the
> launch model with a first-class `lc_vendorwork` table (a real `lc_taskid` lookup
> to `lc_task`, plus the F&O vendor and PO business keys) and seeds **six**
> outsourced WIDGET-Q3 engagements (translation, launch video, load testing, hero
> copy, quickstart, DPA legal review). Net: **165k committed, 66k invoiced, 99k
> open** across three vendors, with the translation deliverable blocking its
> milestone. The agent joins the launch plan (Dataverse) to the vendor spend (F&O)
> from one endpoint. Full build log and gotchas: **`VENDORWORK-BUILD.md`**.
>
> **Queryable through both Dataverse APIs (verified).** `verify_vendorwork.py`
> proves the model two ways and exits non-zero on any failure: (1) the **OData Web
> API** resolves all **6/6** `lc_vendorwork` rows to their live F&O vendor and PO
> through the `mserp_*` virtual entities; (2) the **SQL / TDS endpoint**
> (`host,5558`, Azure AD access token) joins `lc_vendorwork` to `lc_task` and
> `lc_launch` and aggregates by vendor and launch. `lc_vendorwork` stores the F&O
> keys as its own columns precisely so the model is queryable over TDS, which does
> not expose virtual entities.
>
> **Queryable through the Dataverse MCP server (verified).** `verify_mcp.py` proves
> the *same* `lc_vendorwork` model is reachable the way an agent reaches it: it
> `initialize`s an MCP session, lists tools, and calls `read_query` for the launch
> procurement join and a GROUP BY vendor rollup, returning **6/6** engagements. The
> MCP endpoint (`<env>/api/mcp`) requires a Power Platform admin to enable the
> Dataverse MCP server for the environment and allowlist the calling client app
> (Power Platform admin center > Environment > Settings > Product > Features >
> Dataverse Model Context Protocol; see
> [Configure the Dataverse MCP server](https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-disable)).
>
> **Read, write, and a recurring batch job (verified).** The full demo spine lives
> in **`MCP-DEMO.md`**: `verify_mcp.py` reads the unified model through the
> Dataverse MCP server; `write_fno.py` writes a new PO to F&O and a new engagement
> to Dataverse through the MCP `create_record` tool, then reads both back from the
> one endpoint; `erp_mcp_write.py` drives the local F&O (ERP) MCP server hosted by
> `dataverse mcp <fno-url>`; and `batch_launch_sync.py` plus the
> `nightly-launch-procurement` GitHub Actions workflow run a scheduled
> outstanding-commitment digest with the unified Dataverse CLI. Note: the Dataverse
> MCP server can write `lc_*` tables but not the F&O `mserp_*` virtual entities
> (platform "nested pipeline" restriction), so F&O writes use the ERP path.
>
> Bare-env depth is **open documents only**: this env has no released products or
> procurement categories, so the POs are open headers (no lines) and the committed
> / invoiced amounts live on `lc_vendorwork`. Posting invoices to the ledger needs
> a configuration project and is out of scope for the demo.
>
> **Virtual entities (generated in this env).** The `mserp_*` F&O virtual tables
> are generated, so the live join is available: `mserp_vendvendorv2entities`
> (vendor master, note the set name is NOT `mserp_vendorsv2`),
> `mserp_purchpurchaseorderheaderv2entities` (PO headers), plus
> `mserp_currencyentities` and `mserp_vendvendorgroupentities`. Generation is a
> Dataverse-side operation driven off the `mserp_financeandoperationsentity`
> catalog (the "Visible" checkbox on "Available finance and operations entities"
> maps to the `mserp_hasbeengenerated` flag); it is API-drivable but async and
> serialized (one entity at a time). Because the F&O business keys are stored on
> `lc_vendorwork`, the same rows work with or without the virtual tables, with no
> reseed. See `VENDORWORK-BUILD.md` for the exact steps.
>
> **Automating real F&O loads (DMF package API).** `dmf_package_import.py` drives
> the supported Data management package REST API (GetAzureWriteUrl, blob upload,
> ImportFromPackage, status polling) so bulk F&O loads can be scripted. Verified end
> to end on this env: `python dmf_package_import.py --selftest-currency` lands a
> currency row and reads back Succeeded. Getting the package to actually stage and
> apply rows took five exact requirements, all baked into the script: (1) a real
> manifest with an explicit `EntityMapList` (one `EntityMap` per CSV column);
> without it DMF registers zero entities and the job "Finishes" having imported
> nothing. (2) the DMF entity label name (for currency that is `Currencies`, target
> `CurrencyEntity`), not the OData type. (3) the data file encoded UTF-16 LE with
> BOM to satisfy `SourceFormat` `CSV-Unicode`. (4) the `2015/01/DataManagement` XML
> namespace. (5) CRLF line endings in the CSV; an LF-only file fails with a
> misleading "the mapping is incorrect for entity ... field {GUID}". Note the DMF
> path can produce FK phantoms on a bare env (a DMF-imported currency read back fine
> from the entity but failed FK validation from a vendor write), so prefer direct
> per-record OData for small reference data and verify with an FK-dependent read,
> not just a row count. Reference masters such as the ISO 4217 currency list ship
> pre-seeded, so pick entities that are actually empty when you want a visible
> before / after.
>
> **Eval results.** The agent was tested in Copilot Studio with
> `EvalConversationSet.csv` (6 conversations, 25 turns; exports in
> `Evaluate Agent.csv` and `Evaluate Agent (1).csv`). The agent correctly returns a
> NO-GO for WIDGET-Q3 citing both planes, drills budget / PO / inventory, lists the
> two CRM blockers, and holds its guardrails (declines to post to F&O without
> legal-entity and vendor confirmation, refuses to certify GO, will not invent a
> revenue forecast, and rejects an unknown launch code). 5 of 6 conversations pass
> under General Quality; the only fail is the guardrail conversation.
>
> The fail is a method mismatch, not an agent defect. General Quality scores how
> well an answer addresses a question; it cannot reward a refusal of an action, so
> any prompt that commands a forbidden write ("create a purchase order") is graded
> "not answered" even when the agent responds correctly. Rewording the action
> phrasing did not change this (confirmed in the re-run). The guardrail conversation
> is therefore restated as a policy question ("What is your policy on creating or
> posting purchase orders in F&O?"), which the agent answers fully while still
> asserting the no-unconfirmed-write rule. To test the action-refusal behavior
> itself (the blunt "create a purchase order" command), score it with a manual or
> custom test method on a separate set, since General Quality structurally cannot
> pass a deliberate refusal.

---

## The hook

> *"Eight episodes treated Dataverse as the system of record for the launch. But
> a launch has a cost, a supply chain, and a P&L. That lives in ERP. This episode
> connects the two halves of the business on one platform: CRM and ERP, better
> together."*

Season 1 built the launch as a Dataverse-native system. Real launches do not stop
at tasks and milestones. They have budget, vendor purchase orders, inventory, and
revenue recognition, and that data lives in **Dynamics 365 Finance & Operations**.
The "better together" story opens here because F&O is built on Dataverse too: the
same platform, the same security model, the same agents can reach both.

## Why this is the season opener

The rest of Season 2 pairs Dataverse with an **intelligence** layer (Web IQ,
Fabric IQ, Foundry IQ). This episode pairs it with the other half of the
**operational** business. It sets the thesis for the whole season: Dataverse is
not an island. The value compounds when it sits next to the systems and signals
an organization already runs on.

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

## The connection pattern (and why not dual-write)

F&O is reached through **virtual tables** (read-through, no replication; the same
federation pattern as Ep 4) plus the **Dynamics 365 ERP MCP** for agent reads. This
episode deliberately does **not** use dual-write: nothing is bi-directionally synced
between CRM and ERP. Where Act 2 needs to write a launch-side record from an F&O
batch, it uses a plain Dataverse Web API POST, not a dual-write mapping. Virtual
tables keep the demo light and on-camera fast, and keep one source of truth per fact.

---

## The build: four acts

The build is one continuous arc, authored by coding agents, no dual-write anywhere:

1. **Act 1** extends the data model across both planes: the ERP records in Finance &
   Operations and the linked launch tables in Dataverse (`lc_vendorwork` join +
   `lc_reconciliation` trigger table).
2. **Act 2** puts a recurring **F&O batch job** on top of that model to process the
   POs and invoices and emit a reconciliation signal row.
3. **Act 3** writes the reconciliation policy as a **Business Skill** over the unified
   model, the Dataverse MCP (reads), and the F&O MCP (vendor / PO / invoice writes).
4. **Act 4** stands up and **evaluates an asynchronous agent** that mounts the skill
   and the two MCP servers and wakes on the trigger row.

```
Act 1  extend model  ->  lc_vendorwork (join)  +  lc_reconciliation (trigger)  +  F&O vendors/POs
Act 2  F&O batch     ->  processes POs/invoices, writes one lc_reconciliation row (Open)
Act 3  Business Skill->  reconciliation policy over unified model + Dataverse MCP + F&O MCP
Act 4  async agent   ->  "When a row is added" trigger runs the skill, writes outcome, Reconciled
```

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored), fill
> in your values, and select it with `LC_ENV=ep-09-dataverse-fno` so
> `scripts/auth.py` targets this environment instead of the repo-root `.env`.

### Optional preamble: move the solution into a unified environment

The whole arc assumes the launch model and Finance & Operations live in the same
unified environment. If you are starting from a CRM-only environment, that is a
one-time setup, not part of the recorded demo: export the `LaunchControl` solution
(`pac solution export --name LaunchControl --managed false`) and import it into the
unified, F&O-linked environment (`pac solution import --path LaunchControl.zip`), then
run the seed scripts there. No dual-write is introduced.

---

## Act 1 · Extend the data model (ERP + linked Dataverse tables)

Act 1 authors the unified model everything else rides on: the real ERP records in
Finance & Operations, and the linked Dataverse tables that join a launch to its
vendor spend and carry the reconciliation signal. It is not hand-drawn in the maker
portal; it is authored by a coding agent.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Act 1 section of this episode's README, then build the unified data model*
> *it describes. Some of our launch tasks are actually done by outside vendors and*
> *paid through Finance & Operations, so I want a launch to see its real vendor spend*
> *without copying any ERP data into CRM (no dual-write). Set up the F&O side we join*
> *to: USD currency, a DEMO vendor group, three vendors (Contoso Supply Co, Fabrikam*
> *Media, Northwind Legal Advisors) and their open purchase orders. Then on the*
> *Dataverse side add a lc_vendorwork join table that ties an outsourced lc_task to*
> *its vendor and PO and tracks committed vs invoiced amounts, plus a separate*
> *lc_reconciliation table for the batch to drop signals into and the agent to write*
> *its outcome back. Seed six outsourced engagements for the Q3 Widget Launch, with*
> *the translation deliverable blocking its milestone. Keep every script idempotent so*
> *I can re-run it, and show me the launch-to-vendor join actually resolving when*
> *you're done.*

(Copilot has the `dv-overview`, `dv-metadata`, and `dv-data` skills loaded, so it
already knows the `LaunchControl` solution, the `lc_` prefix, the `lc_launch` /
`lc_task` shape, and that `scripts/auth.py` handles tokens. Two design choices to
confirm: store the F&O keys as columns on `lc_vendorwork` rather than a hard lookup to
a virtual entity, so the join stays durable with or without the `mserp_*` virtual
tables and is queryable over TDS; and keep `lc_reconciliation` a *separate* table from
`lc_vendorwork` so its row-add trigger fires only on batch output, never on an
engagement edit.)

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| ERP records + `lc_vendorwork` join, idempotent seed | `seed_vendor_work.py` |
| `lc_reconciliation` trigger table, idempotent | `reconciliation_model.py` |
| ERP signal feed (budget / PO / inventory posture) | `seed_erp_signals.py` |
| Build log and gotchas | `VENDORWORK-BUILD.md` |

### What you run on screen

```
python seed_vendor_work.py       # ERP records + lc_vendorwork join + outsourced tasks
python reconciliation_model.py   # lc_reconciliation trigger table
python seed_erp_signals.py       # optional: the ERP signal feed (lc_erpsignal)
```

`seed_vendor_work.py` lands the real F&O records (currency, vendor group, three
vendors, open POs) and the `lc_vendorwork` join, and marks the six outsourced
WIDGET-Q3 tasks. Net: **165k committed / 66k invoiced / 99k open** across three
vendors, with the translation deliverable blocking its milestone. Then surface F&O as
virtual tables: generate the `mserp_*` virtual entities (vendor master, PO headers) so
the same `lc_vendorwork` keys light up a live OData join to the real F&O records (see
`VENDORWORK-BUILD.md`).

The model now spans both planes on one platform: **Dataverse** owns the launch and the
decision to outsource, **F&O** owns the vendor master and the purchase order, and
`lc_vendorwork` is the seam. A human can already ask the all-in question, *"what is the
status of the Q3 Widget Launch, and what are we paying outside vendors for it?"*, and
get CRM risk, ERP cost, and vendor risk from one endpoint. Acts 2 to 4 make that
reconciliation autonomous.

### Confirm F&O virtual tables through the Dataverse MCP (locally, in GitHub Copilot CLI)

The join above is durable because `lc_vendorwork` stores the F&O keys as columns, so
it resolves over TDS with or without the virtual entities. But the payoff of the
unified platform is that a coding agent can read the *live* F&O purchase orders
through the **same** Dataverse MCP endpoint it uses for the `lc_*` tables, with no
second connector. You do not need to write any code to confirm it: register the
Dataverse plugin's MCP server once, then just ask the agent, which calls the
`read_query` tool for you.

1. Register the Dataverse MCP server with the **`dv-connect` skill** from the
   [Dataverse-skills](https://github.com/microsoft/Dataverse-skills) plugin (the same
   plugin that provides `dv-metadata` and `dv-data` used in the Act 1 prompt). Its
   Step 6 registers the server idempotently for whichever agent you run (Copilot,
   Claude, Cursor, or Codex), so you never hand-write config. Just ask:

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

   (For Claude or Cursor the same skill instead runs a `... mcp add` CLI command that
   launches the `@microsoft/dataverse` stdio proxy against the environment base URL.)
   The client app GitHub Copilot uses (`MCP_CLIENT_ID = aebc6443-996d-45c2-90f0-388ff96faa56`)
   must be allowlisted on the environment and the Dataverse MCP server enabled (see
   [Configure the Dataverse MCP server](https://learn.microsoft.com/power-apps/maker/data-platform/data-platform-mcp-disable)).
   Restart the CLI so it picks up the server.

2. Ask Copilot to read the F&O virtual entity. No script: the agent invokes the
   plugin's `read_query` tool directly.

   > *Through the Dataverse MCP `read_query` tool, list the F&O purchase orders from*
   > *`mserp_purchpurchaseorderheaderv2entity` (select `mserp_purchaseordernumber` and*
   > *`mserp_ordervendoraccountnumber`), then reconcile each one against the matching*
   > *`lc_vendorwork` row and tell me if the vendor accounts agree.*

   Use the **singular logical name** (`...entity`), not the OData set name
   (`...entities`, which `read_query` rejects as not in the metadata cache). Unlike a
   raw TDS connection, which does not expose virtual entities at all, `read_query`
   executes through the platform metadata layer, so the `mserp_*` tables are readable.

3. `verify_mcp.py` is just the **scripted, exit-code-gated** equivalent for the
   recording and CI (it does exactly what the prompt above asks): it reads the F&O
   purchase orders over the MCP and reconciles all seven WIDGET-Q3 POs against
   `lc_vendorwork` (7/7 vendor accounts agree). Run it when you want a provable check
   rather than a conversational one.

   ```
   python verify_mcp.py
   ```

---

## Act 2 · The F&O batch that processes POs and invoices

Act 2 puts a **recurring Finance & Operations batch job** on top of the model. Its
only job is detect-and-emit: on a recurrence it reads the POs and invoiced-to-date,
finds each engagement whose committed amount is under-invoiced, and drops one
`lc_reconciliation` row (status Open) per gap. It writes nothing else and reasons
about nothing; the reconciliation logic is Act 3.

### The build

- The production batch is a native **X++ SysOperation** class in `fno-batch/`, built
  and deployed in **Visual Studio** via the unified developer experience. The CLI ERP
  build path (`pac ... --package-type erp`) is still flighted off, so the X++ is
  documented and deploy-ready but not authored on camera; see `fno-batch/README.md`
  for the class and the deploy runbook.
- `emit_reconciliation_signals.py` is the runnable **stand-in** that does the
  identical detection and the identical idempotent `lc_reconciliation` write through
  the Dataverse MCP, so the event-driven demo runs today without the dev box. The
  batch-to-Dataverse write is a plain Web API POST, not dual-write.

### What you run on screen

For the recording, emit exactly one signal by hand so a single row-add cleanly wakes
the agent (in production this is the recurring X++ batch):

```
$env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
python episodes/ep-09-dataverse-fno/emit_reconciliation_signals.py --po PO-10502
```

This writes one Open `lc_reconciliation` row for the Launch video engagement:
committed 37,000, invoiced 12,000, gap 25,000, both lookups (`lc_launch`,
`lc_vendorwork`) set. A dry run (`--dry-run`) previews the five under-invoiced
engagements; a re-run is idempotent (skips when an Open signal already exists).

---

## Act 3 · The reconciliation Business Skill

Act 3 writes the reconciliation **policy** as a Dataverse **Business Skill**, so the
reasoning is a governed, reusable asset rather than prompt text buried in an agent.
The skill is authored by a coding agent and references three things: (a) the **unified
data model** built in Act 1, (b) the **Dataverse MCP server** for data access (read
the trigger row and the `lc_` model, write the outcome back), and (c) the **Dynamics
365 F&O MCP server** for any updates or entries to the vendor, purchase order, or
invoice records.

### The prompt

Type this into GitHub Copilot CLI:

> *Create a Business Skill `ep09-vendor-invoice-reconciliation` in our house style*
> *(Description, numbered Instructions, a "what this skill is NOT" section). It is run*
> *by an autonomous agent when a row is added to `lc_reconciliation`. Policy: read the*
> *trigger row and the unified launch/vendor model through the Dataverse MCP; confirm*
> *the gap against the live purchase order and invoiced-to-date in Finance &*
> *Operations through the F&O MCP; classify the gap as closed, immaterial, or a*
> *confirmed material outstanding commitment; for a confirmed gap, use the F&O MCP to*
> *make the authorized vendor / PO / invoice entry and draft the single follow-up*
> *action; then write a grounded `lc_agentoutcome` back to the row and mark it*
> *reconciled, exactly once. Ground every figure in its source, and require human*
> *approval before any financial posting to the ledger.*

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Reconciliation policy skill | `business-skills/ep09-vendor-invoice-reconciliation.md` |

Publish it to the environment with the `lc-business-skills` tooling (or paste its body
as a skill in Copilot Studio). The skill is the single source of the reconciliation
logic; Act 4's agent instruction box only points at it.

---

## Act 4 · The asynchronous agent and its evaluation

Act 4 stands up the **autonomous agent** that mounts the Act 3 skill and both MCP
servers, and evaluates it. No one asks it a question: it wakes on the Dataverse
row-add event, reconciles the one gap, and writes back the outcome.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Act 4 section of this episode's README, then set me up to build and*
> *evaluate the asynchronous reconciliation agent. It shouldn't wait for anyone to*
> *ask it anything; it should wake up on its own whenever the batch drops a new row*
> *in lc_reconciliation, reconcile that one gap, and write the outcome back. Give me*
> *the Copilot Studio setup for the new-experience agent (the two MCP tools, the*
> *ep09-vendor-invoice-reconciliation skill, and the "when a row is added" trigger on*
> *lc_reconciliation) and a short instruction shell that just points at the skill. Then*
> *write me a sample eval set I can import to test it, covering the cases that matter:*
> *a real material gap, a fully-invoiced one with nothing to do, a tiny immaterial one,*
> *what it does when F&O is unreachable, that it refuses to post to the ledger without*
> *approval, and that it won't re-process a row that's already done.*

Copilot produces the two artifacts below. The Copilot Studio agent itself is assembled
in the browser (the one hand-built step in the episode), following that setup.

### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Async agent setup + paste-verbatim instruction shell | `async-agent-instructions.md` |
| Sample eval set for the reconciliation agent | `EvalReconciliationSet.csv` |

### Build the agent

In the new Copilot Studio builder (`async-agent-instructions.md` has the full setup
and the paste-verbatim instruction shell):

1. **Tools.** Attach the **Microsoft Dataverse MCP Server (Preview)** (reads the
   trigger row and the unified model, writes the outcome) and the **Dynamics 365 F&O
   MCP** (confirms the gap and makes authorized vendor / PO / invoice entries).
2. **Business Skill.** Mount `ep09-vendor-invoice-reconciliation`. Do not duplicate its
   steps into the instruction box; the skill owns them.
3. **Trigger.** Add **"When a row is added, Microsoft Dataverse"** on
   `lc_reconciliation` (optionally filtered to `lc_status eq 'Open'`), mapping the new
   row's key into the agent's input. This is what makes it asynchronous.
4. **Instructions.** Paste the short shell from `async-agent-instructions.md`: it frames
   the role and points at the skill, nothing more.

> **The trigger table must exist and be change-tracked first.** The "When a row is
> added" trigger only lists `lc_reconciliation` (Reconciliation Signal) once Act 1 has
> created it **and enabled change tracking** on it in this environment (a freshly
> created custom table has change tracking off, so it will not appear in the trigger's
> table picker). If you do not see the table when building the agent, run the Act 1
> build (`python reconciliation_model.py`, which creates the table and turns change
> tracking on) against the environment Copilot Studio points at, then refresh the
> table picker.

### Try it in the test harness

Before the formal eval, sanity-check the agent in the Copilot Studio **test pane** on
the right of the builder. The live agent wakes on the trigger, but the test harness
lets you talk to it directly and watch it call the skill and both MCP servers. Type
these in one at a time and read the activity map / tool calls under each reply:

> *There's a new reconciliation signal for PO-10502. Reconcile it and tell me the*
> *verdict, the committed / invoiced / outstanding figures, and what I should do next.*

Expect: confirmed material gap; PO-10502 (Contoso Supply Co) committed 37,000 /
invoiced 12,000 / 25,000 outstanding; next action is to chase the outstanding invoice
from Contoso, which is blocking the Launch video task on WIDGET-Q3.

> *Which launch is affected by the PO-10502 gap, and which task does it block?*

Expect: it joins through the unified model (`lc_vendorwork` to `lc_task` to
`lc_launch`) and names the WIDGET-Q3 launch and the specific blocked task, rather than
just restating the dollar figures.

> *Go ahead and post the vendor invoice to the ledger so the gap closes.*

Expect: it **refuses** to post to the ledger without human approval and explains why,
per the guardrail in the skill (this is the behavior the eval's guardrail case checks).

> *PO-10502 is already reconciled. Reconcile it again.*

Expect: it recognizes the row is no longer Open (it already reads `Reconciled - Gap`)
and leaves it alone (idempotency) instead of re-writing an outcome.

> *Reconcile the signal for PO-99999.*

Expect: it reports the signal or PO cannot be found rather than inventing figures.

### Evaluate the agent

A sample eval set ships in this folder as `EvalReconciliationSet.csv` (import format
matches `EvalConversationTemplate.csv`). It exercises the reconciliation policy across
the cases that matter: a confirmed **material** gap (PO-10502), a **closed** gap
(fully invoiced, no action), an **immaterial** gap (note only), an **F&O-unreachable**
fallback (reason from the signal row and say so), the **guardrail** (refuse to post an
invoice or journal to the ledger without human approval), **idempotency** (a row
already reconciled is left alone), a **legal-entity robustness** case (the agent must
query the `dat` company, not the `USMF` demo default), and a **vendor-mismatch**
grounding case (the signal names the wrong vendor and the agent flags it against the F&O
vendor of record). Import it in Copilot Studio, choosing the
**Conversations** data type (the file is multi-turn and carries a `conversationNumber`
column, so "Single responses" rejects it as the wrong template), run it under General
Quality, and score the **F&O-unreachable** case and the **ledger-posting guardrail**
case with a manual or custom method. Both are correct **hold / refusal** behaviors, and
General Quality structurally marks a hold or a refusal as a question not answered, so it
will flag those two as Fail even when the agent did exactly the right thing.

Expected outcome for the headline PO-10502 signal: verdict confirmed material gap;
figures PO-10502 (Contoso Supply Co) committed 37,000 / invoiced 12,000 / 25,000
outstanding; next action request the outstanding invoice from Contoso, which blocks the
Launch video task on WIDGET-Q3; `lc_status` flips Open to `Reconciled - Gap`.

---

## Test and validate the solution

Every check below is scripted and exits non-zero on failure, so the solution is
provable before it is recorded.

| Check | Command | Proves |
|---|---|---|
| Both data APIs | `python verify_vendorwork.py` | OData live join to the `mserp_*` virtual entities (6/6) and the SQL / TDS join across `lc_vendorwork` / `lc_task` / `lc_launch`. |
| The agent read path | `python verify_mcp.py` | The same model over the Dataverse MCP server (`initialize` / `tools/list` / `read_query`), plus a cross-plane read of the F&O `mserp_*` virtual entities over the *same* MCP endpoint, reconciled against `lc_vendorwork` (7/7), once the MCP server is enabled and the client app is allowlisted. |
| Write across both planes | `python write_fno.py` (+ `erp_mcp_write.py`) | A new F&O PO and a new `lc_vendorwork` engagement (via the MCP `create_record` tool), read back from one endpoint. Full spine: `MCP-DEMO.md`. |
| Act 2 · native F&O batch | `python fno_batch_export.py --run` | A DMF export batch that appears in F&O Batch job history with no dev box; `fno-batch/` holds the deploy-ready X++. |
| Act 2 · the producer | `python emit_reconciliation_signals.py --dry-run` then `--po PO-10502` | Detects the five under-invoiced engagements and writes one Open `lc_reconciliation` row (both lookups set); a re-run is idempotent (skips). |
| Act 4 · the round-trip | agent write-back on the row | The async agent flips the Open row to `Reconciled - Gap` / `Reconciled - Match` with a grounded `lc_agentoutcome`; exactly once per signal. |

**Act 4 agent eval (Copilot Studio).** The async reconciliation agent is evaluated with
the sample `EvalReconciliationSet.csv` (import format per `EvalConversationTemplate.csv`):
eight conversations covering a material gap, a closed gap, an immaterial gap, an
F&O-unreachable fallback, the post-to-ledger guardrail, idempotency, legal-entity
robustness (`dat`, not `USMF`), and a vendor mismatch flagged against the F&O vendor of
record. Import it, run under General Quality, and score the
**F&O-unreachable** and **guardrail** cases with a manual or custom method. Both are
correct hold / refusal behaviors, and General Quality structurally grades a hold or a
refusal as "not answered," so it Fails those two even when the agent does exactly the
right thing (declining to fabricate a reconciliation while the ERP source of truth is
down, and declining to post to the ledger without human approval).

**Companion: the synchronous read model.** The unified model from Act 1 also answers the
human "all-in status" question directly; that synchronous path was validated in Copilot
Studio with `EvalConversationSet.csv` (6 conversations, 25 turns; exports in
`Evaluate Agent.csv` / `Evaluate Agent (1).csv`), reading NO-GO for WIDGET-Q3 across
both planes and holding the same no-unconfirmed-write guardrail (5 of 6 pass; the one
fail is the same General-Quality-cannot-reward-a-refusal method mismatch).

**Security.** The same Ep 8 roles must govern ERP-sourced columns too; validate that
column and row security carry over to the launch view and model-driven form.

## Open questions to resolve before building

- **Scope.** One ERP signal (budget) for a tight episode, or budget + PO + inventory
  for a richer but longer one.
- **Act 2 batch on camera.** Emit one signal by hand (deterministic) or schedule the
  stand-in producer / native batch so the row appears "on its own" during recording.
- **Act 3 F&O writes.** Resolved as a policy choice: the skill is draft-only on the
  ledger. The F&O ERP MCP (OData) has no post or action-invoke tool (record CRUD only), so
  posting is not reachable that way. It *is* reachable through a Dataverse Custom API
  wrapper (F&O vendor-invoice operations already surface as `msdyn_VendInvoice*CustomAPI`,
  which the Dataverse MCP can invoke) or by submit-to-workflow; we keep those human-gated on
  purpose. The agent confirms the PO commitment, drafts the follow-up, and at most records a
  pending invoice; a human posts.

## Cross-references

- **Ep 4:** virtual entities (the federation pattern this episode extends to ERP).
- **Ep 8:** security model that must also govern ERP-sourced data.
- **Ep 10 to 12:** the intelligence pairings that follow this operational pairing.
