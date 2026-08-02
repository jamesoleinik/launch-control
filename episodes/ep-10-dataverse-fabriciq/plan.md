# Ep 10 build plan: Dataverse + Fabric IQ

This runbook reflects the current architecture choice: a Power BI Direct Lake
semantic model over the Lakehouse SQL analytics endpoint, consumed through a
report and the Fabric IQ Copilot plugin (the Fabric Data Agent path is a paid-
capacity upgrade; the Eventhouse + KQL path was evaluated and archived in
`setup_eventhouse.py`). It tracks what is already built and what remains.

## One-line goal

Use two AI planes:
1. Copilot Studio agent writes `lc_statusupdate` in Dataverse when launch risk is high.
2. A Power BI Direct Lake semantic model over the Lakehouse SQL endpoint unifies
   launch, F&O invoice, and vendor-risk data; the report and the Fabric IQ Copilot
   plugin surface it for questions and escalation review.

The bridge is low-latency Fabric Link (Dataverse to OneLake Lakehouse Delta,
queried via the SQL analytics endpoint).

## Status now

Completed:
- Track Changes enabled on `lc_*` tables.
- Fabric Link active from Dataverse env to LaunchControl workspace.
- LaunchControl Lakehouse active over Fabric Link; SQL analytics endpoint reachable.
- Live Fabric Link table set (verified against the SQL endpoint):
  - Dataverse mirror: `lc_launch`, `lc_task`, `lc_statusupdate`, `lc_vendorwork`,
    `lc_milestone`, `lc_teammember`.
  - F&O ERP mirror: `vendtable` (vendor master), `vendtransopen` (open invoices).
    Note: the live tables are `vendtable` / `vendtransopen`, not `fno_*`.
  - Vendor enrichment / ProcureIQ risk are no longer native tables (lost with a
    recreated lakehouse); they are now inlined as `vw_vendor_enrichment` /
    `vw_vendor_risk` VALUES-views in `semantic_views.sql` for portability.
- Fabric Link completeness check: `lc_erpsignal` (3 rows, ChangeTrackingEnabled)
  is NOT in the Link's selected tables. To add it: maker portal > the table >
  Analyze > Link to Microsoft Fabric > Manage tables. Not currently required by
  the Power BI model; fold it in once added.
- Eventhouse + KQL path (eventhouse `LaunchControlEH`, `fn_live_red_updates`,
  `fn_vendor_360_risk`, etc.) evaluated then archived in `setup_eventhouse.py`;
  the 4-way vendor-360 join now runs as T-SQL in the semantic views.
- `show_replication_latency.py` created for latency distribution output.
- Historical baseline seeded: 5 launches (`EP11-HIST-01..05`), 60 tasks, 5 snapshots.
- `lc_vendorwork` refreshed with realistic values for V0001/V0002/V0003.
- E2E write-path validated with `trigger_red_health.py`:
  - Dataverse RED writes replicated and queryable via the Lakehouse SQL endpoint in about 58s.
- `semantic_views.sql` applied live (7 views, all return rows).
- Direct Lake semantic model `Launch Control 360` published programmatically via
  `setup_powerbi_report.py --create-model` (Fabric REST, TMSL); confirmed
  queryable end-to-end with a DAX `executeQueries` call.
- `analyst_agent_instructions.md` created for Plane 2 agent.
- `setup_fabric_data_agent.py` created for portal documentation + verification.

**Pivoted (Operations Agent dead end):**
- Fabric Operations Agent PA flow action stuck on "Waiting for flow to be saved" (portal bug).
- Replaced with two Copilot Studio agents + Fabric Data Agent (connected agent pattern).
- `setup_operations_agent.py` and Operations Agent JSON artifacts retained for reference.

In progress:
- Fabric Data Agent creation in portal (Step C below).
- Launch Analyst agent creation in Copilot Studio (Step D below).

Blocked:
- Fabric Data Agent creation is blocked on this workspace because it is on a trial
  capacity. The create dialog returns: "Can't create data agents in this
  workspace. An admin needs to change the SKU type for your organization's Fabric
  capacity."
- Per Microsoft Fabric feature parity guidance, trial capacities don't support
  most capacity-gated features unless explicitly footnoted. Fabric Data Agent is
  capacity-gated and currently unavailable in this trial workspace.

Chosen path while on trial (no capacity blocker):
- Consume the Lakehouse through a **Power BI Direct Lake semantic model** + report
  ("Launch Control 360") and the **Fabric IQ** Copilot plugin, instead of a Fabric
  Data Agent. Power BI Direct Lake and Fabric IQ run on trial capacity. The unified
  three-source data (Dataverse launches + F&O invoices + vendor intel) is exposed by
  `semantic_views.sql`. Build steps: sections C-F below and `powerbi_report_spec.md`.
- The Fabric Data Agent + Launch Analyst connected-agent path (sections H-J) remains
  documented as the upgrade once the workspace moves to a paid F/P SKU.

## Prerequisites and local config

1. Copy `.env.example` to `.env` (gitignored) in this folder.
2. Set values for:
   - `DATAVERSE_URL`
   - `FABRIC_WORKSPACE_ID`
   - `FABRIC_WORKSPACE_NAME`
   - `FABRIC_LAKEHOUSE_ID`
   - `FABRIC_LAKEHOUSE_NAME`
   - (the archived Eventhouse path also uses `FABRIC_KQL_CLUSTER_URI` / `FABRIC_KQL_DATABASE_NAME`)
3. Select env:
   - PowerShell: `$env:LC_ENV = "ep-10-dataverse-fabriciq"`
4. Set encoding:
   - PowerShell: `$env:PYTHONIOENCODING = "utf-8"`

## Build checklist

### A. Lakehouse substrate (done)
- [x] Confirm Fabric Link Lakehouse + SQL analytics endpoint (Eventhouse path archived).
- [x] Create/verify the Fabric Link Delta tables over the Lakehouse.
- [x] Seed native `VendorEnrichment` table (internal performance).
- [x] Seed native `ExternalVendorRisk` table (ProcureIQ external market intelligence).
  - V0001-V0003: match vendors in live launches, with differentiated risk profiles.
  - V0004 (Pacific Rim Components): medium risk, in external DB but not in any Dataverse launch.
  - V0005 (Nexus Cloud Services): critical risk, in external DB but not in any Dataverse launch.
- [x] Seed supplementary native tables via `setup_lakehouse_tables.py`.
- [x] Express the analytics as T-SQL over the Lakehouse SQL endpoint (in the Launch
      Analyst agent): live RED updates, per-blocker vendor context, cross-launch RED
      baseline, and the full 360-degree vendor risk join. (KQL-function equivalents
      are archived in `setup_eventhouse.py`.)

Commands:
```bash
python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --dry-run
python episodes/ep-10-dataverse-fabriciq/setup_lakehouse_tables.py --apply
```

### B. Dataverse trigger write path (done)
- [x] Implement `trigger_red_health.py` for RED status writes.
- [x] Validate replication by watching Lakehouse SQL visibility.

Command:
```bash
python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --watch 300
```

### C. Semantic views over the Lakehouse (done)
- [x] Author `semantic_views.sql`: `vw_launch_health`, `vw_vendor_360`,
      `vw_launch_vendor_exposure` (the tri-source launch x invoice x vendor fact),
      `vw_red_status_feed`, `vw_watchlist_vendors`.
- [x] Apply the views to the Lakehouse SQL analytics endpoint.

Commands:
```bash
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --print-views
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views --dry-run
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views
```
(or paste `semantic_views.sql` into the Fabric SQL query editor.)

### D. Power BI Direct Lake semantic model + report
- [x] Publish a Direct Lake semantic model (`Launch Control 360`) over the seven
      views, programmatically via the Fabric REST API (TMSL). Idempotent
      (updateDefinition if it already exists).
- [x] Add report relationships and DAX measures from `powerbi_report_spec.md`.
- [x] Build the "Launch Control 360" report (4 pages: Launch Health, Vendor 360,
      Launch x Vendor Exposure, Blind Spots) programmatically and publish it,
      bound to the model (PBIR byConnection). Idempotent.
- [x] Confirm the model is queryable (DAX `executeQueries` returns rows).

Commands:
```bash
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model --dry-run
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-report
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --verify
```

Reference: `episodes/ep-10-dataverse-fabriciq/powerbi_report_spec.md`

### E. Fabric IQ in Copilot (portal step)
- [ ] Enable the Fabric IQ plugin in Microsoft 365 Copilot (Power BI MCP server).
      This is the only non-scriptable step (UI toggle).
- [ ] Point it at the "Launch Control 360" semantic model in the LaunchControl workspace.
- [ ] Confirm natural-language answers, e.g. "Which launch's RED rate is most
      anomalous vs. the median?" and "Open ERP invoice exposure for EP11-DEMO-01?".

### F. Final episode proof
- [x] Run RED trigger and confirm Dataverse to Lakehouse SQL timing.
- [ ] Capture proof points:
  - Dataverse write timestamp
  - Lakehouse SQL visibility timestamp (target: <60s)
  - Power BI report refresh showing the new RED update + vendor exposure
  - Fabric IQ answer in Copilot reflecting the same launch
- [x] Add timing summary to `README.md`.

### G. Policy/tenant diagnostics (done, archived)
- [x] `diagnose_dataactivator_policy.py`: documents Operations Agent DLP blocker.
- [x] `setup_operations_agent.py`: automation for Operations Agent (retained for reference).

## Optional upgrade: Fabric Data Agent connected-agent path (needs F/P capacity)

Blocked on trial capacity; enable after the workspace moves to a paid F or P SKU.
Reads the same Lakehouse, so no data rework is needed.

### H. Fabric Data Agent (portal step)
- [ ] Create a Fabric Data Agent in the LaunchControl workspace over the Lakehouse SQL endpoint.
- [ ] Paste instructions from `setup_fabric_data_agent.py --instructions`; add table hints; publish.
- [ ] Run `setup_fabric_data_agent.py --verify` to capture and export the agent config.

### I. Launch Analyst Copilot Studio agent (portal step)
- [ ] Create "Launch Analyst" agent; add the Fabric Data Agent as a connected agent.
- [ ] Create the "Analyze RED launch" topic from `analyst_agent_instructions.md`; add Teams action; publish.

### J. Wire Plane 1 to Plane 2 (portal step)
- [ ] In Plane 1, add a Power Automate flow (input `launch_id`) that calls the Launch Analyst endpoint after a RED write.
- [ ] Test agent-to-agent handoff end to end.

## The "why Fabric" narrative

The episode answer to "why does this need Fabric?" is:

1. **V0004 and V0005 exist only in ExternalVendorRisk.** Fabric holds risk intelligence
   about vendors the operational system (Dataverse) hasn't engaged yet. An alert about
   Nexus Cloud Services (V0005, Critical market risk) would be invisible to Dataverse alone.
2. **The vendor-360 view joins 4 sources**: `vw_vendor_enrichment` (internal ops),
   `vw_vendor_risk` (ProcureIQ market intel), `vendtransopen` (ERP open balance),
   `vendtable` (ERP master).
   None of these would be natural Dataverse rows under the boundary rule.
3. **Cross-launch anomaly detection** via `vw_launch_health`. The question "is this
   launch's RED rate an outlier?" requires aggregating across all historical launches: a
   semantic pattern, not a per-row Dataverse query.

## Notes and constraints

- In `eppcdemo1fno`, `lc_health` values are:
  - Green: `10600601`  |  Yellow: `10600602`  |  Red: `10600603`
- For `lc_statusupdate` launch binding, use `lc_launchid@odata.bind`
- Fabric Data Agent and connected agents are preview features (2025). Expect portal UI changes.
- Keep real IDs and URLs in `.env` only. Do not commit environment identifiers.
