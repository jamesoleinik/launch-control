# Episode 11: Dataverse + Fabric IQ (structured state meets semantic data)

**Status:** 🛠️ In Build (Phase 2: Data substrate) · 🎬 Not yet recorded
**Build status (this pass):** Dataverse-to-OneLake link setup in progress. Prerequisite check: Track Changes must be enabled on all `lc_*` custom tables before linking to Fabric.
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Fabric IQ (semantic data layer over Microsoft Fabric) · ⭐ Dataverse MCP Server (transactional state) · ⭐ Autonomous agent runtime (event + recurrence triggers) · ⭐ Reasoning over governed analytics, not just rows
**Layer:** 🔵 Layer 2 (proactive automation) over a semantic data foundation
**Coding agent:** Copilot Studio (autonomous agent)
**Runtime:** Copilot Studio autonomous agent + Dataverse MCP + Fabric IQ
**Runtime showcased:** the **autonomous agent** pattern (reuses the Season 1 Sentinel build, archived at `episodes/archive/ep-10-autonomous-agents/` and the code at `agents/launch-sentinel/`)

> **Building this episode?** Follow `plan.md` in this folder. It is the
> self-contained build runbook for a dedicated CLI session: prerequisites, the
> Fabric IQ ontology steps, the autonomous-agent wiring (reusing
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
meaning** of the data. Fabric IQ is the semantic intelligence layer over
Microsoft Fabric. It turns raw enterprise data into business meaning with
ontologies, KPIs, trends, and graph reasoning, so an agent can ask "is this
launch tracking abnormally?" and get an answer grounded in trusted analytics.

> **Sequencing note (Season 2):** This is Episode 11. For launch announcements,
> we may present this Fabric-first story ahead of Episode 10 to spotlight the
> Link data / Link to Fabric experience refresh.

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

## Build steps (outline)

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored),
> fill in your values (`FABRIC_WORKSPACE_ID`, `FABRIC_ONTOLOGY_ID`), and select
> it with `LC_ENV=ep-11-dataverse-fabriciq`.

> **Prerequisite check:** All `lc_*` custom tables must have **Track Changes enabled**
> before they can be linked to Fabric OneLake. Run:
> ```
> python scripts/python/check_track_changes.py
> ```
> If any tables show "DISABLED", enable Track Changes in the table properties (Dataverse
> admin portal or Power Platform admin center). This is required for near real-time
> sync to OneLake.
>
> **Fabric Link replication latency (measured, eppcdemo1fno, 2026-07-21):**
>
> | Metric | Value |
> |--------|-------|
> | Median | ~11 seconds |
> | P90 | ~36 seconds |
> | P95 | ~48 seconds |
> | Max observed | ~69 seconds |
> | Throughput | ~80 rows/min avg, 136/min peak |
> | Cold-start (first sync) | ~10-12 minutes |
>
> Under sustained write load the Fabric Link runs continuously (new micro-batch every
> ~60s). The first sync after a long idle period is ~10-12 minutes (cold-start warm-up).
> All rows in a 2,863-row bulk test replicated within 5 minutes once the link was warm.

1. Reuse the autonomous agent shell from `agents/launch-sentinel/` (triggers,
   idempotency, the `lc_statusupdate` effector).
2. Connect Fabric IQ as a tool / knowledge source the agent can query for the
   semantic baseline.
3. Encode the decision: escalate only when the live Dataverse state diverges from
   the Fabric IQ norm beyond a threshold.
4. Validate that no analytical artifact is duplicated into Dataverse rows.

## Open questions to resolve before building

- **Access.** Confirm a Microsoft Fabric environment with Fabric IQ available to
  demo against, and that the launch data (or a representative dataset) is modeled.
- **How Fabric IQ attaches** to a Copilot Studio agent (tool vs knowledge vs MCP)
  at record time; confirm the current path.
- **Baseline data.** The anomaly beat needs enough historical launches (real or
  seeded) for a credible "norm."

## Cross-references

- **`episodes/archive/ep-10-autonomous-agents/`** and `agents/launch-sentinel/`:
  the autonomous runtime this episode reuses.
- **Ep 10:** the Web IQ agent (external signal); this is the internal-semantic counterpart.
- **Ep 13** (convergence): the Fabric IQ agent runs alongside Web IQ and Foundry
  IQ on one launch.
