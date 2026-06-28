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
> **Open blocker (F&O data).** The F&O side ships as a bare `dat` template company
> with no demo data, and OData writes fail at the X++ layer, so the ERP signals the
> money shot needs cannot be scripted. The environment must be provisioned WITH
> demo data (admin center / LCS demo topology) or loaded via the Data Management
> Framework. Verify with `python fno_readiness.py` (exits 0 when ready).

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

## The money shot

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
