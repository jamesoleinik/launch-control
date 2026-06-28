# Ep 11 build plan: Dataverse + Fabric IQ (parallel CLI session)

This plan lets a separate Copilot CLI session build Episode 11 independently of
the Ep 9 (F&O) and Ep 10 (Web IQ) sessions. Read it top to bottom, then work the
checklist. The episode narrative and headline result live in `README.md`; this file is
the build runbook.

## One-line goal

An **autonomous** Copilot Studio agent that reasons over two planes: the live
per-launch state (Dataverse MCP) and the **semantic baseline** of the business
(Fabric IQ ontology over Microsoft Fabric). It fires on a schedule, compares the
live record to the modeled norm, and escalates only genuine anomalies by writing a
`lc_statusupdate` row.

## Status entering this session

- **TODO (most work):** this episode is the least built of the three. It needs a
  Fabric IQ ontology created in the Fabric workspace, the autonomous agent wired
  to it, and enough historical launch data to make "normal" credible.
- **Reusable assets:** the autonomous runtime already exists at
  `agents/launch-sentinel/` (triggers, idempotency, the `lc_statusupdate`
  effector). This episode reuses it; do not rebuild it from scratch.

## Prerequisites / local config

1. Copy `.env.example` to `.env` in this folder (gitignored) and fill in:
   - `DATAVERSE_URL` (env holding the `lc_` launch tables).
   - `FABRIC_WORKSPACE_ID` (the Fabric workspace that will hold the ontology; the
     provisioned workspace is named "EPPC", a Fabric F-SKU capacity).
   - `FABRIC_ONTOLOGY_ID` (filled in after you create the ontology, step B).
   - `POWERBI_WORKSPACE` (the `powerbi://api.powerbi.com/v1.0/myorg/<workspace>`
     connection string).
   - `TENANT_ID`.
2. Select this env: PowerShell `$env:LC_ENV = "ep-11-dataverse-fabriciq"`.
3. Set `$env:PYTHONIOENCODING="utf-8"` before running Python.

## Connection facts (confirmed)

- Connecting a Copilot Studio agent to Fabric uses the **Fabric IQ Ontology MCP**
  server (Microsoft, Premium, Preview): "enables agents to interact with Microsoft
  Fabric IQ Ontology using the Model Context Protocol."
- Auth: Login with Microsoft Entra ID.
- Required connection inputs: **Workspace ID** (the Fabric workspace containing the
  ontology) and **Ontology ID** (the ID of the Fabric IQ ontology). Both go in
  `.env` and are pasted into the MCP tool connection in the builder.

## Build checklist

### A. Get the data into Fabric (scriptable + portal)
- [ ] Resolve the Fabric **Workspace ID** for the "EPPC" workspace via the Power BI
      / Fabric REST API using an az token (`az account get-access-token --resource
      https://api.fabric.microsoft.com`), or read it from the workspace URL in the
      Fabric portal. Record it in `.env` as `FABRIC_WORKSPACE_ID`.
- [ ] Link the Dataverse launch data into Fabric (Dataverse-to-OneLake / Link to
      Microsoft Fabric, or a semantic model over the `lc_` tables) so the ontology
      has something to model.
- [ ] Ensure there is enough **historical launch data** (real or seeded) for a
      credible "norm". The anomaly beat needs many launches, not one. Reuse the
      rich seed scripts (`scripts/python/seed_launch_demo_rich.py`) and consider
      seeding several historical launches with varying blocker counts.

### B. Build the Fabric IQ ontology (Fabric portal, browser)
- [ ] In the EPPC workspace, create a **Fabric IQ ontology** over the launch
      semantic data (entities: launch, milestone, task; measures: blocker count,
      slip rate, readiness trajectory).
- [ ] Capture the **Ontology ID** and put it in `.env` as `FABRIC_ONTOLOGY_ID`.
- [ ] Sanity-check the ontology answers "what is a normal blocker count for this
      phase?" before wiring an agent to it.

### C. Build the autonomous agent (Copilot Studio, browser)
- [ ] **Create the Business Skill in Dataverse.** Load
      `business-skills/ep11-anomaly-escalation.md` into the agent's Dataverse env
      as a `skill` record (POST to `/api/data/v9.2/skills` with `name`,
      `uniquename` = `lc_ep11anomaly`, `description`, `body` = the markdown,
      `origin` = 0; idempotent-delete any existing row with that uniquename first,
      exactly as the Ep 9 session created `lc_ep09erpreadiness`). The agent must
      follow this skill.
- [ ] Start from the `agents/launch-sentinel/` pattern (triggers, idempotency,
      `lc_statusupdate` effector). Reuse, do not reinvent.
- [ ] Add **Tool: Dataverse MCP Server (Preview)** for the live per-launch facts
      and as the write target for findings.
- [ ] Add **Tool: Fabric IQ Ontology MCP** with the Workspace ID + Ontology ID
      from `.env`. Authenticate with Entra ID.
- [ ] Write the agent Instructions (create `agent-instructions.md` in this folder,
      mirror the Ep 9 format): role = launch analyst that watches the curve;
      escalate only when the live Dataverse state diverges from the Fabric IQ norm
      beyond a threshold; write one `lc_statusupdate` per genuine anomaly; never
      duplicate an analytical artifact into a Dataverse row.
- [ ] Set the trigger: a scheduled morning sweep (and/or a "task blocks" event).

### D. Validate the headline result
- [ ] Run the scheduled sweep with no human prompt.
- [ ] Dataverse reports the live blocker count; Fabric IQ reports the modeled norm;
      the agent writes a grounded `lc_statusupdate` only when the live count is a
      true outlier (for example 8 vs a modeled 2 to 3, a 95th-percentile anomaly).
- [ ] Confirm idempotency: re-running the sweep does not double-post.

## Deliverables this session should produce

1. `episodes/ep-11-dataverse-fabriciq/agent-instructions.md` (paste-ready
   Instructions, same shape as Ep 9's).
2. A short script or note documenting how the Workspace ID + Ontology ID were
   obtained (no GUIDs in committed files; reference `.env`).
3. A "Build status" line in `README.md` recording what was built and validated.

## Guardrails

- No em-dashes in committed prose. No real env URLs / tenant IDs / GUIDs / capacity
  IDs / connection strings in any committed file (placeholders only; actuals live
  in the gitignored `.env`).
- Honor the "complement, not duplicate" rule: learned KPI baselines and cross-launch
  trends stay in Fabric IQ, never copied into Dataverse rows.

## Risks / gating

- **Biggest gate:** Fabric IQ availability and how it attaches to a Copilot Studio
  agent at record time (tool vs knowledge vs MCP). Confirm the current path early;
  if Fabric IQ ontology creation is not yet available in the tenant, this episode
  stays a spec until it is.
- **Baseline credibility:** without enough historical launches, the anomaly beat is
  not believable. Seed generously.

## Hand-off / coordination with the other sessions

- Ep 11 shares the `lc_` launch model with the other episodes but adds a separate
  Fabric substrate. If you seed historical launches, coordinate with whoever owns
  the shared Dataverse env so seeds do not collide, or use your own env.
- This is the heaviest build; expect to deliver the ontology + agent over more than
  one pass. Land the scriptable parts (Workspace ID resolution, Dataverse-to-Fabric
  link, historical seed) first so the browser steps are pure wiring.
