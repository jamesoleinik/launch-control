# Episode 9: Dataverse + F&O (CRM and ERP, better together)

**Status:** ✍️ Draft (Season 2 opener) · 🎬 Not yet recorded
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Dataverse and Dynamics 365 Finance & Operations on one platform · ⭐ Dual-write / virtual tables across CRM and ERP · ⭐ One launch record enriched with ERP cost and supply signal
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

## The integration options (pick one as the hero)

1. **Virtual tables over F&O:** surface F&O entities (for example a project
   budget or a purchase order) as virtual tables in the launch environment.
   Read-through, no replication. Mirrors the Ep 4 virtual-entity pattern.
2. **Dual-write:** bi-directional, near-real-time sync of selected entities
   between the CRM and F&O environments. Heavier, but writes flow both ways.

Recommended hero for the episode: **virtual tables** (lighter, on-camera fast,
and consistent with the Ep 4 federation story). Mention dual-write as the
production-grade alternative.

## The headline result

> *"What is the all-in status of the Q3 Widget Launch, and what are we paying
> outside vendors for it?"*

- **Dataverse** returns the go-to-market state: readiness NO-GO, two blockers.
- **F&O** returns the financial state: the launch is over its approved budget, and
  open vendor POs are still uninvoiced.
- **The join (`lc_vendorwork`)** returns the outsourced spend: 165k committed
  across six engagements and three vendors, only 66k invoiced, 99k open, and the
  translation deliverable (an open PO, not yet received) is blocking a milestone.
- **Synthesis:** the launch is not just behind on tasks; it is over budget and
  waiting on a supplier the launch team is paying through ERP. CRM risk, ERP cost,
  and vendor risk on one record.

## Build steps (outline)

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored),
> fill in your values, and select it with `LC_ENV=ep-09-dataverse-fno` so
> `scripts/auth.py` targets this environment instead of the repo-root `.env`.

1. Identify the F&O entities worth surfacing (budget, PO, inventory for the SKU).
2. Stand up the connection (virtual tables or dual-write) between the launch
   environment and F&O.
3. Seed the launch/procurement join: `python seed_vendor_work.py` creates the real
   F&O vendors and open POs, extends the model with `lc_vendorwork` (lookup to
   `lc_task` plus the F&O keys), and marks the outsourced WIDGET-Q3 tasks.
4. Verify both data APIs: `python verify_vendorwork.py` proves the OData live join
   to the `mserp_*` virtual entities (6/6) and the SQL / TDS join across
   `lc_vendorwork` / `lc_task` / `lc_launch`. Full build log: `VENDORWORK-BUILD.md`.
5. Verify the agent path: `python verify_mcp.py` proves the same model over the
   Dataverse MCP server (`initialize` / `tools/list` / `read_query`), once the MCP
   server is enabled and the client app is allowlisted for the environment.
6. Add the ERP fields to the launch view / model-driven form.
7. Validate security: the same Ep 8 roles must govern ERP-sourced columns too.

## Open questions to resolve before building

- **Access.** Confirm we have an F&O environment and licensing to demo against.
  This is the biggest gating risk in Season 2.
- **Hero pattern.** Virtual tables vs dual-write for the recorded demo.
- **Scope.** One ERP signal (budget) for a tight episode, or budget + PO +
  inventory for a richer but longer one.

## Cross-references

- **Ep 4:** virtual entities (the federation pattern this episode extends to ERP).
- **Ep 8:** security model that must also govern ERP-sourced data.
- **Ep 10 to 12:** the intelligence pairings that follow this operational pairing.
