# Episode 10: Dataverse + Fabric IQ (two-plane AI architecture)

**Status:** 🛠️ In Build (Phase 5: Power BI semantic model + Fabric IQ consumption) · 🎬 Not yet recorded
**Build status (this pass):**
- Track Changes ENABLED on all 7 `lc_*` tables (confirmed 2026-07-21)
- Fabric Link (low-latency sync) active: eppcdemo1fno → LaunchControl workspace
- All 6 `lc_*` tables live in Fabric (1 launch, 12 tasks, 6 milestones, 5 status updates)
- Replication latency benchmarked: **median 11s, P95 48s, max 69s** under load (2,863 rows)
- Eventhouse `LaunchControlEH` created + KQL database provisioned
- 6 external Delta tables over Fabric Link lakehouse (4 Dataverse + 2 F&O tables)
- `VendorEnrichment` native KQL table: internal vendor performance (V0001/V0002/V0003)
- `ExternalVendorRisk` native KQL table: ProcureIQ external market intelligence (V0001-V0005)
- 4 KQL functions: `fn_live_red_updates`, `fn_vendor_risk_for_blocker` (updated), `fn_blocker_pattern_history`, `fn_vendor_360_risk` (new)
- Historical baseline seeded: 5 `EP11-HIST-*` launches, 60 tasks, 5 baseline status snapshots
- `lc_vendorwork` updated with realistic V0001/V0002/V0003 financial and due-date values
- **E2E data flow verified**: Dataverse write → Fabric Link → KQL eventhouse in **58s** (lag=65s from createdon)
- **Architecture pivot**: Fabric Data Agent (capacity-gated: needs F/P SKU) replaced for the trial-capacity build by a **Power BI Direct Lake semantic model** over the Lakehouse, consumed via a Power BI report and the **Fabric IQ** Copilot plugin; see `powerbi_report_spec.md`. The Data Agent path remains documented as the F/P-capacity upgrade.
- Next steps: apply `semantic_views.sql`, build the Direct Lake model + Launch Control 360 report, wire Fabric IQ in Copilot
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Fabric IQ (semantic data layer + Copilot plugin over Microsoft Fabric) · ⭐ Dataverse MCP Server (transactional state) · ⭐ Power BI Direct Lake semantic model (over the Lakehouse SQL endpoint) · ⭐ Fabric Data Agent (optional upgrade on F/P capacity)
**Layer:** 🔵 Layer 2 (proactive automation) over a semantic data foundation
**Coding agent:** Copilot Studio (two agents: Launch Control + Launch Analyst)
**Runtime:** Copilot Studio (Plane 1) + Dataverse MCP + Fabric Link + Lakehouse SQL + Power BI Direct Lake + Fabric IQ (Plane 2)

> **Building this episode?** Follow `plan.md` in this folder. It is the
> self-contained build runbook: prerequisites, Lakehouse table setup, semantic
> views (`semantic_views.sql`), the Power BI Direct Lake model + report, and the
> Fabric IQ Copilot wiring (`powerbi_report_spec.md`), plus E2E validation.

---

## The hook

> *"Dataverse knows the state of this one launch. Fabric IQ knows what 'normal'
> looks like across every launch we have ever run — and what the external risk
> data says about the vendors involved. This agent reasons over all three."*

The Web IQ episode reached outside the tenant for live signal. This one stays
inside, but reaches **up a level**: from individual rows to the **semantic
meaning** of the data across sources — and introduces a second AI agent that
lives in Fabric, triggered by the first.

> **Sequencing note (Season 2):** This is Episode 10. For launch announcements,
> we may present this Fabric-first story ahead of Episode 11 to spotlight the
> low-latency Fabric Link / Lakehouse experience.

## The two-plane architecture

```
User prompt
    |
[Plane 1: Copilot Studio "Launch Control" agent]
    |  Dataverse MCP: writes lc_statusupdate (health=RED=10600603)
    |  then calls Plane 2 with the launch_id
    |
    v  ~11s median (low-latency Fabric Link)
[LaunchControl Lakehouse — SQL analytics endpoint]
    |
    |  Tables from Fabric Link (Dataverse):
    |    lc_statusupdate, lc_task, lc_launch, lc_vendorwork
    |  Tables from Fabric Link (F&O ERP):
    |    fno_vendtable, fno_vendtransopen
    |  Supplementary tables (native, seeded by setup_lakehouse_tables.py):
    |    VendorEnrichment   — internal delivery performance (V0001-V0003)
    |    ExternalVendorRisk — ProcureIQ market intelligence (V0001-V0005)
    |                         V0004/V0005 exist HERE but NOT in Dataverse
    |
    v
[Semantic layer: semantic_views.sql over the Lakehouse SQL endpoint]
    |    vw_launch_health, vw_vendor_360, vw_launch_vendor_exposure,
    |    vw_red_status_feed, vw_watchlist_vendors
    |
    v
[Plane 2: Power BI Direct Lake semantic model - "Launch Control 360"]
    |    Star model over the five views + DAX measures
    |    (RED Rate vs Median, Total Open ERP Exposure, High-Risk Vendors)
    |
    +--> Power BI report: Launch Health / Vendor 360 /
    |    Launch x Vendor Exposure / Blind spots
    |
    +--> Fabric IQ plugin in Microsoft 365 Copilot (Power BI MCP server):
         "Which launch's RED rate is most anomalous vs. the median?"
         "Open ERP invoice exposure for vendors on EP11-DEMO-01?"
         "Which high-risk ProcureIQ vendors have no active launch work?"
```

The bridge is **low-latency Fabric Link** (2026 feature). Benchmarked:
median **11s**, P95 **48s**, all rows within 5 minutes under load.
E2E confirmed: Dataverse write → Lakehouse queryable in **~58s**.

The key multi-source story: the semantic model answers questions that no single
system could, joining live Dataverse status, F&O ERP invoice exposure, internal
delivery history, AND external ProcureIQ risk signals in one Direct Lake model,
reachable from a Power BI report or from Fabric IQ in Copilot.

> **Architecture note:** We evaluated using a Fabric Eventhouse (KQL database)
> as an additional layer but opted for simplicity: the Lakehouse SQL analytics
> endpoint is queryable directly by the Fabric Data Agent with no extra
> infrastructure. The Eventhouse path (archived in `setup_eventhouse.py`) is
> worth revisiting if sub-second query latency or KQL's time-series functions
> become relevant.

## Why this is a complement, not a duplicate (the design rule)

The boundary test stays the same: *would this naturally be a row I query, relate,
secure, or transact?*

- **Yes -> Dataverse.** The live transactional state of a single launch.
- **No, it is analytical / cross-entity / multi-source -> Fabric IQ.**
  Trends across all launches, external risk intelligence, ERP financial exposure.

The clearest signal: V0004 and V0005 exist only in `ExternalVendorRisk`. Dataverse
has never heard of them. Fabric can alert on their risk profile before they ever
appear in an operational record.

## The two agents

**Plane 1 — Launch Control agent** (existing):
- Receives user updates about launch health
- Writes `lc_statusupdate` rows to Dataverse via Dataverse MCP
- After writing a RED status, calls Plane 2 with the launch_id

**Plane 2 — Launch Analyst agent** (new, this episode):
- Receives a launch_id from Plane 1
- Calls the Fabric Data Agent as a connected agent
- Gets cross-source analysis: live RED updates + vendor 360 risk + anomaly context
- Posts a grounded escalation to Teams

## Build steps

> **Local config.** Copy `.env.example` to `.env` (gitignored), fill in your values.
> Key vars: `FABRIC_WORKSPACE_ID`, `FABRIC_WORKSPACE_NAME`, `FABRIC_LAKEHOUSE_NAME`,
> `FABRIC_LAKEHOUSE_ID`, `DATAVERSE_URL`.
> Select with `LC_ENV=ep-10-dataverse-fabriciq`.

> **Replication latency (measured, eppcdemo1fno, 2026-07-21):**
>
> | Metric | Value |
> |--------|-------|
> | Median | ~11 seconds |
> | P95 | ~48 seconds |
> | E2E (write → Lakehouse SQL) | ~58 seconds |
> | Cold-start (first sync) | ~10-12 minutes |

### Step 1: Seed Lakehouse supplementary tables

```bash
python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --dry-run
python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --apply
python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --verify
```

This writes two Delta tables directly to OneLake alongside the Fabric Link tables:
- **`VendorEnrichment`** — internal delivery performance for V0001/V0002/V0003
- **`ExternalVendorRisk`** — ProcureIQ market intelligence for V0001-V0005
  (V0004/V0005 exist here only — not in any Dataverse launch)

Prerequisites: `pip install pandas pyarrow deltalake azure-identity`

### Step 2: Trigger test (Dataverse write path)

```bash
python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --wait 60
```

Writes two RED status updates to Dataverse and waits 60s for Fabric Link replication.

### Step 3: Create the Fabric Data Agent (portal step)

```bash
# Get instructions + table descriptions to paste into the portal:
python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --instructions

# After creation, verify and export the agent config:
python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --verify
```

Portal steps: Fabric workspace > "+ New item" > "AI agent" > LaunchControl Lakehouse
(SQL endpoint) > select all 8 tables > paste instructions > publish.

### Step 4: Create the Launch Analyst Copilot Studio agent (portal step)

Reference: `episodes/ep-10-dataverse-fabriciq/analyst_agent_instructions.md`

Portal steps:
1. Create "Launch Analyst" agent in Copilot Studio.
2. Add the Fabric Data Agent as a connected agent (Knowledge > Connected agents).
3. Create the "Analyze RED launch" topic.
4. Add Teams "Post message" action for escalation.
5. Publish.

### Step 5: Wire Plane 1 → Plane 2

In the Launch Control agent (Plane 1), add a PA flow action after the RED status write:
- Flow input: `launch_id`
- Flow calls the Launch Analyst agent's HTTP endpoint.

### Step 6: E2E validation

```bash
python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --wait 60
```

Then in Copilot Studio, call the Launch Analyst agent: "Analyze this launch: EP11-DEMO-01."
Confirm the Teams escalation appears with vendor risk + anomaly context.

## Archived artifacts

The following files document the original Operations Agent approach, which was
blocked by a Fabric portal UI bug (PA flow action stuck on "Waiting for flow to be saved"):

- `setup_operations_agent.py` — Fabric Operations Agent REST API automation
- `setup_eventhouse.py` — KQL Eventhouse setup (now marked ARCHIVED)
- `operations_agent_schema.json`, `operations_agent_template.json` — agent definition exports
- `diagnose_dataactivator_policy.py` — DLP diagnostic for the shared_dataactivator blocker

### Step 4: Full E2E validation

```bash
python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --watch 300
```

Observe:
1. RED health status update written to Dataverse
2. Fabric Link replicates to OneLake (~11s median, ~58s E2E including KQL availability)
3. Operations Agent rule fires (requires Step 3 complete)
4. Teams alert received with vendor context from VendorEnrichment join

## Cross-references

- **`episodes/archive/ep-11-autonomous-agents/`** and `agents/launch-sentinel/`:
  the autonomous runtime this episode reuses.
- **Ep 11:** the Web IQ agent (external signal); this is the internal-semantic counterpart.
- **Ep 13** (convergence): the Fabric IQ agent runs alongside Web IQ and Foundry
  IQ on one launch.
