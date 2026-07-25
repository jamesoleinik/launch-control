# Episode 11: Dataverse + Fabric IQ (two-plane AI architecture)

**Status:** 🛠️ In Build (Phase 4: Operations Agent) · 🎬 Not yet recorded
**Build status (this pass):**
- Track Changes ENABLED on all 7 `lc_*` tables (confirmed 2026-07-21)
- Fabric Link (low-latency sync) active: eppcdemo1fno → LaunchControl workspace
- All 6 `lc_*` tables live in Fabric (1 launch, 12 tasks, 6 milestones, 5 status updates)
- Replication latency benchmarked: **median 11s, P95 48s, max 69s** under load (2,863 rows)
- Eventhouse `LaunchControlEH` created + KQL database provisioned
- 6 external Delta tables over Fabric Link lakehouse (4 Dataverse + 2 F&O tables)
- `VendorEnrichment` native KQL table seeded (V0001/V0002/V0003 with names + risk scores)
- 3 KQL functions deployed: `fn_live_red_updates`, `fn_vendor_risk_for_blocker`, `fn_blocker_pattern_history`
- Historical baseline seeded: 5 `EP11-HIST-*` launches, 60 tasks, 5 baseline status snapshots
- `lc_vendorwork` updated with realistic V0001/V0002/V0003 financial and due-date values
- **E2E data flow verified**: Dataverse write → Fabric Link → KQL eventhouse in **58s** (lag=65s from createdon)
- `setup_operations_agent.py` added to automate list/export/create for Operations Agent definitions
- Remaining gap: Teams action wiring in Operations Agent designer (portal connection step; see `plan.md`)
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Fabric IQ (semantic data layer over Microsoft Fabric) · ⭐ Dataverse MCP Server (transactional state) · ⭐ Autonomous agent runtime (event + recurrence triggers) · ⭐ Reasoning over governed analytics, not just rows
**Layer:** 🔵 Layer 2 (proactive automation) over a semantic data foundation
**Coding agent:** Copilot Studio (autonomous agent)
**Runtime:** Copilot Studio autonomous agent + Dataverse MCP + Fabric IQ
**Runtime showcased:** the **autonomous agent** pattern (reuses the Season 1 Sentinel build, archived at `episodes/archive/ep-10-autonomous-agents/` and the code at `agents/launch-sentinel/`)

> **Building this episode?** Follow `plan.md` in this folder. It is the
> self-contained build runbook for a dedicated CLI session: prerequisites, the
> eventhouse + Operations Agent wiring, the autonomous-agent wiring (reusing
> `agents/launch-sentinel/`), and the headline validation. This is the heaviest
> Season 2 build; land the scriptable parts first, then the browser wiring. Runs in
> parallel with Ep 9 and Ep 10.

---

## The hook

> *"Dataverse knows the state of this one launch. Fabric IQ knows what 'normal'
> looks like across every launch we have ever run. This agent reasons over both:
> the live record and the semantic model of the business."*

The Web IQ episode reached outside the tenant for live signal. This one stays
inside, but reaches **up a level**: from individual rows to the **semantic
meaning** of the data — and introduces a second AI agent that lives natively in
Fabric, triggered by the first.

> **Sequencing note (Season 2):** This is Episode 11. For launch announcements,
> we may present this Fabric-first story ahead of Episode 10 to spotlight the
> low-latency Fabric Link / Link to Fabric experience refresh.

## The two-plane architecture

This episode demonstrates a pattern none of the prior episodes showed: **two
AI agents in two different runtimes, orchestrated by data**.

```
User prompt
    |
[Copilot Studio agent]  -- Dataverse MCP (live launch state)
    |  writes lc_statusupdate (health=RED=10600603) to Dataverse
    |
    v  ~11s median (low-latency Fabric Link)
[LaunchControl Fabric Lakehouse]  -- lc_* tables as Delta Parquet + F&O vend* tables
    |
    v
[KQL Database: LaunchControlEH]
    |  external Delta tables: lc_statusupdate, lc_task, lc_launch,
    |                         lc_vendorwork, fno_vendtable, fno_vendtransopen
    |  native table: VendorEnrichment (names, on_time_pct, risk_tier)
    |  functions: fn_live_red_updates(), fn_vendor_risk_for_blocker(),
    |             fn_blocker_pattern_history()
    |
[Fabric Operations Agent: LaunchControlOpsAgent]
    |  rule: new lc_statusupdate with lc_health == 10600603 (Red)
    |  → join VendorEnrichment for vendor context
    |  → join fn_blocker_pattern_history() for anomaly baseline
    v
Teams alert: "Q3 Widget: Acme Translations (V0001, High risk, 61% on-time)
              SLA breach. RED is a 95th-pct outlier for this launch phase."
```

The bridge is **low-latency Fabric Link** (2026 feature). Benchmarked in this
environment: median replication latency **11 seconds**, P95 **48 seconds**,
all 2,863 test rows replicated within **5 minutes** under sustained load. E2E
confirmed this session: two RED health status updates written to Dataverse appeared
in the KQL eventhouse in **58 seconds** (lag from `createdon`: 65s).
Run `python episodes/ep-11-dataverse-fabriciq/show_replication_latency.py`
to see the full distribution.

The Fabric Operations Agent adds what the Studio agent cannot: **cross-launch
historical context** from the full data estate, not just the current record.

## Why this is a complement, not a duplicate (the design rule)

The boundary test stays the same: *would this naturally be a row I query, relate,
secure, or transact?*

- **Yes -> Dataverse.** The live transactional state of a single launch: its
  current blockers, owners, readiness score. The system of action.
- **No, it is analytical / cross-entity / historical meaning -> Fabric IQ.**
  Trends across all launches, KPI baselines, anomaly detection, the semantic model
  ("what does a healthy launch curve look like?"). The system of insight.

Dataverse answers "what is true right now for this launch." Fabric IQ answers
"what does that mean against everything we know." You would not store a learned
KPI baseline or a cross-launch trend as a Dataverse row, so you do not.

## The agent: a launch analyst that watches the curve

A natural fit for the **autonomous** runtime. The agent does not wait to be asked;
it watches and reasons.

- **Dataverse MCP** supplies the live per-launch facts and is where the agent
  writes its findings (a `lc_statusupdate` row, same effector as the Season 1
  Sentinel).
- **Fabric IQ** supplies the semantic baseline: is this launch's blocker rate,
  slip rate, or readiness trajectory abnormal relative to the modeled norm?
- The agent fires on an event (a task blocks) or a schedule (the morning sweep),
  compares the live record to the Fabric IQ baseline, and escalates only the
  genuinely abnormal cases.

### The headline result

> Scheduled morning sweep, no human prompt.

1. **Dataverse** says Q3 Widget Launch has 8 blocked tasks.
2. **Fabric IQ** says that at this point in the cycle, the modeled norm is 2 to 3
   blockers; 8 is a 95th-percentile anomaly, and the pattern matches launches that
   later slipped.
3. **The agent writes** a status update: "Q3 Widget is a statistical outlier on
   blocker count for its phase (8 vs a modeled 2 to 3). Historically this pattern
   precedes a slip. Flagging for review." Grounded escalation, not a raw count.

## Build steps

> **Local config.** Copy `.env.example` to `.env` (gitignored), fill in your values.
> Key vars: `FABRIC_WORKSPACE_ID`, `FABRIC_LAKEHOUSE_NAME`, `FABRIC_KQL_CLUSTER_URI`.
> Select with `LC_ENV=ep-11-dataverse-fabriciq`.

> **Prerequisite check:** All `lc_*` custom tables must have **Track Changes enabled**
> before they can be linked to Fabric OneLake. Run:
> ```
> python scripts/python/check_track_changes.py
> ```
>
> **Fabric Link replication latency (measured, eppcdemo1fno, 2026-07-21):**
>
> | Metric | Value |
> |--------|-------|
> | Median | ~11 seconds |
> | P90 | ~36 seconds |
> | P95 | ~48 seconds |
> | Max observed | ~69 seconds |
> | E2E (write → KQL) | ~58 seconds |
> | Cold-start (first sync) | ~10-12 minutes |

### Step 1: Eventhouse + KQL database (DONE)

Eventhouse `LaunchControlEH` created in LaunchControl workspace via Fabric REST API.
KQL database auto-provisioned. All tables and functions deployed with one script.

```bash
# Dry-run first:
python episodes/ep-11-dataverse-fabriciq/setup_eventhouse.py --dry-run

# Apply (idempotent):
python episodes/ep-11-dataverse-fabriciq/setup_eventhouse.py --apply
```

This creates:
- **6 external Delta tables** over the Fabric Link lakehouse (`lc_statusupdate`,
  `lc_task`, `lc_launch`, `lc_vendorwork`, `fno_vendtable`, `fno_vendtransopen`)
- **`VendorEnrichment`** native table: vendor names + delivery performance + risk tier
  for V0001 (Acme Translations), V0002 (GlobalTech Licensing), V0003 (SwiftLogix Freight)
- **3 KQL functions**: `fn_live_red_updates()`, `fn_vendor_risk_for_blocker(name)`,
  `fn_blocker_pattern_history()`

### Step 2: E2E trigger test (DONE)

```bash
# Trigger RED health writes and watch for KQL replication:
python episodes/ep-11-dataverse-fabriciq/trigger_red_health.py --apply --watch 300

# With cleanup (removes demo records from Dataverse):
python episodes/ep-11-dataverse-fabriciq/trigger_red_health.py --apply --watch 300 --cleanup
```

**Verified result:** Two vendor-linked RED health updates appeared in KQL in 58 seconds.

### Step 3: Operations Agent (mostly scriptable now)

The Fabric Operations Agent REST API is in Preview. The definition format is now
captured and scriptable in this repo.

Script support:
```bash
# List agents in workspace
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --list

# Export a definition JSON (+ decoded parts folder)
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --export --agent-id <agent-id> --definition episodes/ep-11-dataverse-fabriciq/operations_agent_schema.json

# Render a starter definition from env values
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --render-template --definition episodes/ep-11-dataverse-fabriciq/operations_agent_template.json

# Update an existing agent from definition JSON
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --update --agent-id <agent-id> --definition episodes/ep-11-dataverse-fabriciq/operations_agent_schema.json
```

One-time portal work still needed: wire the final Teams action and confirm rule
behavior in the Operations Agent designer.

Use `.env` for workspace/agent IDs; do not commit tenant-specific IDs.

### Step 4: Full E2E validation

```bash
python episodes/ep-11-dataverse-fabriciq/trigger_red_health.py --apply --watch 300
```

Observe:
1. RED health status update written to Dataverse
2. Fabric Link replicates to OneLake (~11s median, ~58s E2E including KQL availability)
3. Operations Agent rule fires (requires Step 3 complete)
4. Teams alert received with vendor context from VendorEnrichment join

## Cross-references

- **`episodes/archive/ep-10-autonomous-agents/`** and `agents/launch-sentinel/`:
  the autonomous runtime this episode reuses.
- **Ep 10:** the Web IQ agent (external signal); this is the internal-semantic counterpart.
- **Ep 13** (convergence): the Fabric IQ agent runs alongside Web IQ and Foundry
  IQ on one launch.
