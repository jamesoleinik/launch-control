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

## Act 1 · The synchronous readiness agent (build, step by step)

Act 1 is the "ask across both planes" agent: a human asks for a launch's all-in
status and the agent answers by reading the go-to-market state (Dataverse) and the
financial/supply state (F&O) together.

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored), fill
> in your values, and select it with `LC_ENV=ep-09-dataverse-fno` so
> `scripts/auth.py` targets this environment instead of the repo-root `.env`.

### Step 1 · Prompt the coding agent to extend the data model

The data-model extension is not hand-drawn in the maker portal; it is authored by a
coding agent. Type this into GitHub Copilot CLI:

> *Extend the LaunchControl model so outsourced launch work is joined to Finance &*
> *Operations. Create a first-class `lc_vendorwork` table with a real `lc_taskid`*
> *lookup to `lc_task`, and store the F&O business keys on it (`lc_vendoraccount`,*
> *`lc_ponumber`) plus the money the launch team tracks (`lc_committedamount`,*
> *`lc_invoicedamount`, `lc_status`). Then create the real F&O side to join to:*
> *currency USD, a `DEMO` vendor group, three vendors (Contoso Supply Co, Fabrikam*
> *Media, Northwind Legal Advisors) and their open purchase orders. Seed six*
> *outsourced WIDGET-Q3 engagements against those POs, with the translation*
> *deliverable blocking its milestone. Make the script idempotent and re-runnable,*
> *and verify the join resolves from Dataverse to the F&O records.*

(Copilot has the `dv-overview`, `dv-metadata`, and `dv-data` skills loaded, so it
already knows the `LaunchControl` solution, the `lc_` prefix, the `lc_launch` /
`lc_task` shape, and that `scripts/auth.py` handles tokens. Storing the F&O keys as
columns on `lc_vendorwork`, rather than a hard lookup to a virtual entity, is the one
design choice to confirm: it keeps the join durable with or without the `mserp_*`
virtual tables and queryable over TDS.)

#### What Copilot produces

| Artifact | Where it lands |
|---|---|
| Idempotent model + seed script | `seed_vendor_work.py` |
| Build log and gotchas | `VENDORWORK-BUILD.md` |

#### What you run on screen

`python seed_vendor_work.py` creates the real F&O records (currency, vendor group,
three vendors, open POs), extends the launch model with the first-class
`lc_vendorwork` join, and marks the six outsourced WIDGET-Q3 tasks. Net: 165k
committed / 66k invoiced / 99k open across three vendors.

### Step 2 · Seed the ERP signal feed

`python seed_erp_signals.py` lands the clearly labeled `lc_erpsignal` table (budget
over approval, an open vendor PO, an inventory shortfall) in the same environment,
the narrative ERP posture the agent reads through the Dataverse MCP.

### Step 3 · Surface F&O as virtual tables

Generate the `mserp_*` virtual entities (vendor master, PO headers) so the same
`lc_vendorwork` keys light up a live OData join to the real F&O records. See
`VENDORWORK-BUILD.md` for the exact steps.

### Step 4 · Build the agent

In the new Copilot Studio builder, attach the **Dataverse MCP Server (Preview)** and
**Dynamics 365 ERP MCP** tools, publish the `lc_ep09erpreadiness` Business Skill
(`business-skills/ep09-erp-readiness.md`), and paste `agent-instructions.md` into the
Instructions box.

### The headline result (Act 1)

> *"What is the all-in status of the Q3 Widget Launch, and what are we paying
> outside vendors for it?"*

- **Dataverse** returns the go-to-market state: readiness NO-GO, two blockers.
- **F&O** returns the financial state: over the approved budget, open vendor POs
  still uninvoiced.
- **The join (`lc_vendorwork`)** returns the outsourced spend: 165k committed across
  six engagements and three vendors, only 66k invoiced, 99k open, and the translation
  deliverable (an open PO, not yet received) blocking a milestone.
- **Synthesis:** the launch is not just behind on tasks; it is over budget and
  waiting on a supplier the launch team is paying through ERP. CRM risk, ERP cost,
  and vendor risk on one record.

---

## Act 2 · The event-driven reconciliation agent (build, step by step)

Act 1 answers a human's question. Act 2 removes the human from the loop: a recurring
batch emits an event, and an autonomous agent reacts. The chain, no dual-write
anywhere:

```
recurring F&O batch (native X++, or the emit_reconciliation_signals stand-in)
   detects under-invoiced engagements
   -- writes one row -->  lc_reconciliation (status Open)
                                 |
                    "When a row is added" trigger fires
                                 v
   async Copilot Studio agent  +  ep09-vendor-invoice-reconciliation Business Skill
   reads the live PO / invoiced-to-date from F&O (ERP MCP), confirms the gap,
   drafts the follow-up, writes lc_agentoutcome, sets lc_status = Processed
```

The design keeps the two roles clean:

- **Producer** is the recurring **F&O batch**. Its only job is detect-and-emit: for
  each engagement whose committed amount is under-invoiced, drop one
  `lc_reconciliation` row. The production batch is the native X++ SysOperation class
  in `fno-batch/` (built and deployed in Visual Studio via the unified developer
  experience; the CLI ERP build path is still flighted off, so the X++ is documented
  but not authored on camera). `emit_reconciliation_signals.py` is the runnable
  stand-in that does the identical detection and idempotent `lc_reconciliation` write
  through the Dataverse MCP, so the event-driven demo works today.
- **Consumer** is the **asynchronous agent**. It carries no reconciliation logic in
  its instruction box; it pulls in the `ep09-vendor-invoice-reconciliation` Business
  Skill (`business-skills/ep09-vendor-invoice-reconciliation.md`) and reasons over the
  Dataverse and F&O MCP servers. Setup and instructions: `async-agent-instructions.md`.

`lc_reconciliation` is deliberately a separate table from `lc_vendorwork` so the
row-add trigger fires only on batch output, never when an engagement is edited.

Build steps:

1. **Create the trigger table.** `python reconciliation_model.py` creates the
   idempotent `lc_reconciliation` table with lookups to `lc_launch` and
   `lc_vendorwork`.
2. **Emit a signal (the producer).** For the recording, emit exactly one signal by
   hand so a single row-add cleanly wakes the agent:

   ```
   $env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-09-dataverse-fno"
   python episodes/ep-09-dataverse-fno/emit_reconciliation_signals.py --po PO-10502
   ```

   In production this is the native F&O X++ batch (`fno-batch/`, the
   `LcProcurementReconcile` variant) running on a recurrence.
3. **Publish the reconciliation Business Skill** (`ep09-vendor-invoice-reconciliation`)
   so the async agent can pull it in at trigger time.
4. **Build the asynchronous agent.** In Copilot Studio, attach the Dataverse and F&O
   MCP tools, mount the skill, and add a **"When a row is added" trigger on
   `lc_reconciliation`** (optionally filtered to `lc_status eq 'Open'`). Full setup:
   `async-agent-instructions.md`.

### Optional preamble: move the solution into a unified environment

The event-driven arc assumes the launch model and Finance & Operations live in the
same unified environment. If you are starting from a CRM-only environment, that is a
one-time setup, not part of the recorded demo: export the `LaunchControl` solution
(`pac solution export --name LaunchControl --managed false`) and import it into the
unified, F&O-linked environment (`pac solution import --path LaunchControl.zip`), then
run the seed scripts there. No dual-write is introduced.

---

## Test and validate the solution

Every check below is scripted and exits non-zero on failure, so the solution is
provable before it is recorded.

| Check | Command | Proves |
|---|---|---|
| Both data APIs | `python verify_vendorwork.py` | OData live join to the `mserp_*` virtual entities (6/6) and the SQL / TDS join across `lc_vendorwork` / `lc_task` / `lc_launch`. |
| The agent read path | `python verify_mcp.py` | The same model over the Dataverse MCP server (`initialize` / `tools/list` / `read_query`), once the MCP server is enabled and the client app is allowlisted. |
| Write across both planes | `python write_fno.py` (+ `erp_mcp_write.py`) | A new F&O PO and a new `lc_vendorwork` engagement (via the MCP `create_record` tool), read back from one endpoint. Full spine: `MCP-DEMO.md`. |
| Native F&O batch | `python fno_batch_export.py --run` | A DMF export batch that appears in F&O Batch job history with no dev box; `fno-batch/` holds the deploy-ready X++. |
| Act 2 producer | `python emit_reconciliation_signals.py --dry-run` then `--po PO-10502` | Detects the five under-invoiced engagements and writes one Open `lc_reconciliation` row (both lookups set); a re-run is idempotent (skips). |
| Act 2 round-trip | agent write-back on the row | The async agent flips the Open row to `Processed` with a grounded `lc_agentoutcome`; exactly once per signal. |

**Agent eval (Copilot Studio).** Act 1 was tested with `EvalConversationSet.csv`
(6 conversations, 25 turns; exports in `Evaluate Agent.csv` /
`Evaluate Agent (1).csv`). The agent returns NO-GO for WIDGET-Q3 citing both planes,
drills budget / PO / inventory, lists the two CRM blockers, and holds its guardrails
(declines to post to F&O without legal-entity and vendor confirmation, refuses to
certify GO, will not invent a revenue forecast, rejects an unknown launch code). 5 of
6 pass under General Quality; the one fail is a scoring-method mismatch (General
Quality cannot reward an action refusal), not an agent defect, so the guardrail case
is restated as a policy question or scored with a manual method.

**Security.** The same Ep 8 roles must govern ERP-sourced columns too; validate that
column and row security carry over to the launch view and model-driven form.

## Open questions to resolve before building

- **Scope.** One ERP signal (budget) for a tight episode, or budget + PO + inventory
  for a richer but longer one.
- **Act 2 producer on camera.** Emit one signal by hand (deterministic), or schedule
  the stand-in producer so the row appears "on its own" during the recording.

## Cross-references

- **Ep 4:** virtual entities (the federation pattern this episode extends to ERP).
- **Ep 8:** security model that must also govern ERP-sourced data.
- **Ep 10 to 12:** the intelligence pairings that follow this operational pairing.
