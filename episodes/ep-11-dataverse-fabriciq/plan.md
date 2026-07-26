# Ep 11 build plan: Dataverse + Fabric Operations Agent

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
  - native table: `VendorEnrichment` seeded with V0001, V0002, V0003
  - functions: `fn_live_red_updates`, `fn_vendor_risk_for_blocker`,
    `fn_blocker_pattern_history`
- `show_replication_latency.py` created for latency distribution output.
- Historical baseline seeded: 5 launches (`EP11-HIST-01..05`), 60 tasks, 5 snapshots.
- `lc_vendorwork` refreshed with realistic values for V0001/V0002/V0003.
- E2E write-path validated with `trigger_red_health.py`:
  - Dataverse RED writes replicated and queryable in KQL in about 58s.

In progress:
- Operations Agent rule wiring in Fabric portal, then definition capture.

Blocked:
- Final Teams action wiring for Operations Agent requires portal connection details
  not exposed through current scripted endpoints.
- Data Activator connector path may fail with tenant policy restrictions in this
  tenant. PAC/governance API cannot override when connector enablement configs are
  disabled (`DlpConnectorEnablementConfigurationsNotAllowedForTenant`).

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
   - PowerShell: `$env:LC_ENV = "ep-11-dataverse-fabriciq"`
4. Set encoding:
   - PowerShell: `$env:PYTHONIOENCODING = "utf-8"`

## Build checklist

### A. KQL substrate (done)
- [x] Create eventhouse and KQL database.
- [x] Create external Delta tables with impersonation URI form:
  `h@'abfss://<WorkspaceName>@onelake.dfs.fabric.microsoft.com/<Lakehouse>.Lakehouse/Tables/<table>;impersonate'`
- [x] Seed native `VendorEnrichment` table.
- [x] Create KQL helper functions.

Commands:
```bash
python episodes/ep-11-dataverse-fabriciq/setup_eventhouse.py --dry-run
python episodes/ep-11-dataverse-fabriciq/setup_eventhouse.py --apply
```

### B. Dataverse trigger write path (done)
- [x] Implement `trigger_red_health.py` for RED status writes.
- [x] Validate replication by watching KQL visibility.

Command:
```bash
python episodes/ep-11-dataverse-fabriciq/trigger_red_health.py --apply --watch 300
```

### C. Operations Agent automation (partially done)
- [x] Script stable API operations (`setup_operations_agent.py`):
  - list agents
  - export definition via `getDefinition`
  - create from saved definition JSON
  - update definition via `updateDefinition`
  - render starter template definition from `.env`
- [x] Export definition JSON and decode parts locally.
- [ ] One-time portal step: wire Teams action and validate final rule behavior.

Commands:
```bash
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --list
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --export --agent-id <agent-id>
python episodes/ep-11-dataverse-fabriciq/setup_operations_agent.py --create --definition operations_agent_schema.json
python episodes/ep-11-dataverse-fabriciq/diagnose_dataactivator_policy.py
```

### D. Final episode proof
- [x] Run RED trigger and confirm Dataverse to KQL timing.
- [ ] Capture proof points:
  - Dataverse write timestamp
  - KQL visibility timestamp
  - Operations Agent run or Teams alert evidence
- [x] Add timing summary to `README.md`.

## Notes and constraints

- In `eppcdemo1fno`, `lc_health` values are:
  - Green: `10600601`
  - Yellow: `10600602`
  - Red: `10600603`
- For `lc_statusupdate` launch binding, use:
  - `lc_launchid@odata.bind` (not `lc_Launch@odata.bind`)
- Keep real IDs and URLs in `.env` only. Do not commit environment identifiers.
