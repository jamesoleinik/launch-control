# Ep 10 build plan: Dataverse + Fabric Operations Agent

This runbook reflects the current architecture choice: eventhouse + KQL (not
Fabric ontology). It tracks what is already built and what remains to finish the
episode.

## One-line goal

Use two AI planes:
1. Copilot Studio agent writes `lc_statusupdate` in Dataverse when launch risk is high.
2. Fabric Operations Agent detects RED updates in KQL, enriches with vendor context,
   and sends an escalation.

The bridge is low-latency Fabric Link (Dataverse to OneLake to KQL external Delta).

## Status now

Completed:
- Track Changes enabled on `lc_*` tables.
- Fabric Link active from Dataverse env to LaunchControl workspace.
- Eventhouse `LaunchControlEH` and KQL database provisioned.
- `setup_eventhouse.py` created and applied:
  - external Delta tables: `lc_statusupdate`, `lc_task`, `lc_launch`, `lc_vendorwork`,
    `fno_vendtable`, `fno_vendtransopen`
  - native tables: `VendorEnrichment` (internal performance), `ExternalVendorRisk` (ProcureIQ market intel)
  - functions: `fn_live_red_updates`, `fn_vendor_risk_for_blocker` (updated with ExternalVendorRisk),
    `fn_blocker_pattern_history`, `fn_vendor_360_risk` (new: full 360 risk profile)
- `show_replication_latency.py` created for latency distribution output.
- Historical baseline seeded: 5 launches (`EP11-HIST-01..05`), 60 tasks, 5 snapshots.
- `lc_vendorwork` refreshed with realistic values for V0001/V0002/V0003.
- E2E write-path validated with `trigger_red_health.py`:
  - Dataverse RED writes replicated and queryable in KQL in about 58s.
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

Immediate fallback while on trial:
- Keep the Lakehouse data model work (already automated) and complete the demo
  using direct Lakehouse SQL queries + Copilot Studio logic, without a Fabric Data
  Agent connected-agent dependency.
- Re-enable the full Plane 2 connected-agent path after moving the workspace to a
  supported paid capacity (F SKU or P SKU).

## Prerequisites and local config

1. Copy `.env.example` to `.env` (gitignored) in this folder.
2. Set values for:
   - `DATAVERSE_URL`
   - `FABRIC_WORKSPACE_ID`
   - `FABRIC_WORKSPACE_NAME`
   - `FABRIC_LAKEHOUSE_NAME`
   - `FABRIC_KQL_CLUSTER_URI`
   - `FABRIC_KQL_DATABASE_NAME`
3. Select env:
   - PowerShell: `$env:LC_ENV = "ep-10-dataverse-fabriciq"`
4. Set encoding:
   - PowerShell: `$env:PYTHONIOENCODING = "utf-8"`

## Build checklist

### A. KQL substrate (done)
- [x] Create eventhouse and KQL database.
- [x] Create external Delta tables with impersonation URI form.
- [x] Seed native `VendorEnrichment` table (internal performance).
- [x] Seed native `ExternalVendorRisk` table (ProcureIQ external market intelligence).
  - V0001-V0003: match vendors in live launches, with differentiated risk profiles.
  - V0004 (Pacific Rim Components): medium risk, in external DB but not in any Dataverse launch.
  - V0005 (Nexus Cloud Services): critical risk, in external DB but not in any Dataverse launch.
- [x] Create KQL helper functions:
  - `fn_live_red_updates` — all live RED updates
  - `fn_vendor_risk_for_blocker(task_name)` — vendor context for blocked task (updated: now includes ExternalVendorRisk)
  - `fn_blocker_pattern_history` — cross-launch RED baseline
  - `fn_vendor_360_risk(vendor_account)` — NEW: full 360-degree vendor risk profile

Commands:
```bash
python episodes/ep-10-dataverse-fabriciq/setup_eventhouse.py --dry-run
python episodes/ep-10-dataverse-fabriciq/setup_eventhouse.py --apply
```

### B. Dataverse trigger write path (done)
- [x] Implement `trigger_red_health.py` for RED status writes.
- [x] Validate replication by watching KQL visibility.

Command:
```bash
python episodes/ep-10-dataverse-fabriciq/trigger_red_health.py --apply --watch 300
```

### C. Fabric Data Agent (portal step)
- [ ] Create a Fabric Data Agent in the LaunchControl workspace over LaunchControlEH KQL database.
- [ ] Paste instructions from `setup_fabric_data_agent.py --instructions`.
- [ ] Add table descriptions and function hints.
- [ ] Publish the agent endpoint.
- [ ] Run `setup_fabric_data_agent.py --verify` to capture and export the agent config.

Command (generates instructions to paste into portal):
```bash
python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --instructions
python episodes/ep-10-dataverse-fabriciq/setup_fabric_data_agent.py --verify
```

### D. Launch Analyst Copilot Studio agent (portal step)
- [ ] Create "Launch Analyst" agent in Copilot Studio.
- [ ] Add the Fabric Data Agent as a connected agent (Knowledge > Connected agents).
- [ ] Create the "Analyze RED launch" topic from `analyst_agent_instructions.md`.
- [ ] Add Teams "Post message" action for escalation.
- [ ] Publish the agent.
- [ ] Note the agent HTTP endpoint for Plane 1 wiring.

Reference: `episodes/ep-10-dataverse-fabriciq/analyst_agent_instructions.md`

### E. Wire Plane 1 to Plane 2 (portal step)
- [ ] In Plane 1 agent (Launch Control agent), add a Power Automate flow action after RED write:
  - Flow input: `launch_id`
  - Flow calls the Launch Analyst agent's HTTP endpoint.
- [ ] Test agent-to-agent handoff: write RED via Plane 1, confirm Plane 2 escalates.

### F. Final episode proof
- [x] Run RED trigger and confirm Dataverse to KQL timing.
- [ ] Capture proof points:
  - Dataverse write timestamp
  - KQL visibility timestamp (target: <60s)
  - Fabric Data Agent query result showing 360-degree vendor risk
  - Teams alert evidence from Launch Analyst agent
- [x] Add timing summary to `README.md`.

### G. Policy/tenant diagnostics (done, archived)
- [x] `diagnose_dataactivator_policy.py` — documents Operations Agent DLP blocker.
- [x] `setup_operations_agent.py` — automation for Operations Agent (retained for reference).

## The "why Fabric" narrative

The episode answer to "why does this need Fabric?" is:

1. **V0004 and V0005 exist only in ExternalVendorRisk.** Fabric holds risk intelligence
   about vendors the operational system (Dataverse) hasn't engaged yet. An alert about
   Nexus Cloud Services (V0005, Critical market risk) would be invisible to Dataverse alone.
2. **fn_vendor_360_risk joins 4 sources** — VendorEnrichment (internal ops), ExternalVendorRisk
   (ProcureIQ market intel), fno_vendtransopen (ERP open balance), fno_vendtable (ERP master).
   None of these would be natural Dataverse rows under the boundary rule.
3. **Cross-launch anomaly detection** via fn_blocker_pattern_history. The question "is this
   launch's RED rate an outlier?" requires aggregating across all historical launches — a
   semantic pattern, not a per-row Dataverse query.

## Notes and constraints

- In `eppcdemo1fno`, `lc_health` values are:
  - Green: `10600601`  |  Yellow: `10600602`  |  Red: `10600603`
- For `lc_statusupdate` launch binding, use `lc_launchid@odata.bind`
- Fabric Data Agent and connected agents are preview features (2025). Expect portal UI changes.
- Keep real IDs and URLs in `.env` only. Do not commit environment identifiers.
