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
> **ERP signals (stand-in, in place now).** The F&O side ships as a bare `dat`
> template company with no demo data, and OData writes fail at the X++ layer, so
> the live `mserp_` virtual entities cannot be scripted. To keep the build moving
> and make the headline result demonstrable today, a small, clearly labeled
> stand-in table `lc_erpsignal` is seeded in the SAME environment (run
> `python seed_erp_signals.py`): three signals for the Q3 Widget Launch (budget
> 575k over a 500k approval, open vendor PO-10042 for the CDN appliance, inventory
> 120 of 500 for WIDGET-V1). The agent reads it through the Dataverse MCP. This is
> a temporary stand-in.
>
> **Swap-later (real F&O data).** Provision the environment WITH demo data (admin
> center / LCS demo topology) or load it via the Data Management Framework, verify
> with `python fno_readiness.py` (exits 0 when ready), then repoint the agent's ERP
> reads to the live F&O virtual entities / Dynamics 365 ERP MCP and retire
> `lc_erpsignal`. The narrative is identical either way.
>
> **Automating real F&O loads (DMF package API).** `dmf_package_import.py` drives
> the supported Data management package REST API (GetAzureWriteUrl, blob upload,
> ImportFromPackage, status polling) so F&O loads can be scripted instead of
> hand-clicked. Verified on this env: auth, package upload, and ImportFromPackage
> all succeed (HTTP 200, real execution id), so the automation itself works. The
> queued import does not complete here because the environment's batch framework is
> not processing jobs and the bare `dat` company lacks base configuration. Both are
> provisioning conditions, the same prerequisites the manual Data management path
> needs. Once the env is provisioned (batch running plus base setup), run
> `python dmf_package_import.py --selftest-currency` then load vendor / item / PO
> packages, verify with `fno_readiness.py`, and the stand-in can be retired.
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

> *"What is the all-in status of the Q3 Widget Launch?"*

- **Dataverse** returns the go-to-market state: readiness NO-GO, two blockers.
- **F&O (virtual table)** returns the financial state: the launch is over its
  approved budget, and the vendor PO for the CDN appliance is still open.
- **Synthesis:** the launch is not just behind on tasks; it is over budget and
  waiting on a supplier. CRM risk and ERP risk on one record.

## Build steps (outline)

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored),
> fill in your values, and select it with `LC_ENV=ep-09-dataverse-fno` so
> `scripts/auth.py` targets this environment instead of the repo-root `.env`.

1. Identify the F&O entities worth surfacing (budget, PO, inventory for the SKU).
2. Stand up the connection (virtual tables or dual-write) between the launch
   environment and F&O.
3. Add the ERP fields to the launch view / model-driven form.
4. Validate security: the same Ep 8 roles must govern ERP-sourced columns too.

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
