# Ep 10 build plan: Dataverse + Fabric

This runbook is organized around the episode's four on-camera sections. The
architecture choice underneath them is a Power BI Direct Lake semantic model over
the Lakehouse SQL analytics endpoint, consumed through a report and the Fabric
/ Cowork Copilot plugin.

## The four sections (recording arc)

1. **Section 1 - Fabric Link.** Create the fast Dataverse -> OneLake Fabric Link
   for the launch and vendor tables, and confirm the Lakehouse SQL analytics
   endpoint is reachable.
2. **Section 2 - Backfill + measured latency.** Backfill ~100 historical launch
   status records, measure the write -> OneLake replication latency to the second,
   and emit a distribution graph. Deliverable: `measure_sync_latency.py`.
3. **Section 3 - Semantic model + report from a coding agent (no DAX).** Build a
   Power BI Direct Lake semantic model that joins the launch/project data with an
   enrichment dataset, show the model, and generate the report entirely from a
   coding agent. Deliverables: `semantic_views.sql` + `setup_powerbi_report.py`.
4. **Section 4 - Fabric Cowork plugin.** Enable the Fabric Cowork / IQ plugin and
   pull data across the joined model directly in Cowork (the one manual step).

## One-line goal

Use two AI planes:
1. Copilot Studio agent writes `lc_statusupdate` in Dataverse when launch risk is high.
2. A Power BI Direct Lake semantic model over the Lakehouse SQL endpoint unifies
   launch, F&O invoice, and vendor-risk data; the report and the Fabric / Cowork
   Copilot plugin surface it for questions and escalation review.

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
- The 4-way vendor-360 join runs as T-SQL in the semantic views.
- `measure_sync_latency.py` (Section 2 deliverable) backfills tagged status
  records, polls the OneLake mirror with a fresh connection per cycle, and outputs
  the write -> OneLake latency distribution (stats + histogram PNG + CSV). It
  replaces the earlier ad-hoc latency query script.
- Historical baseline seeded: 5 launches (`EP11-HIST-01..05`), 60 tasks, 5 snapshots.
- `lc_vendorwork` refreshed with realistic values for V0001/V0002/V0003.
- E2E write-path validated with `trigger_red_health.py`:
  - Dataverse RED writes replicated and queryable via the Lakehouse SQL endpoint in about 58s.
- `semantic_views.sql` applied live (7 views, all return rows).
- Direct Lake semantic model `Launch Control 360` published programmatically via
  `setup_powerbi_report.py --create-model` (Fabric REST, TMSL); confirmed
  queryable end-to-end with a DAX `executeQueries` call.

Chosen path:
- Consume the Lakehouse through a **Power BI Direct Lake semantic model** + report
  ("Launch Control 360") and the **Fabric** Copilot plugin, instead of a Fabric
  Data Agent. Power BI Direct Lake and Fabric run on trial capacity. The unified
  three-source data (Dataverse launches + F&O invoices + vendor intel) is exposed by
  `semantic_views.sql`. Build steps: sections C-F below and `powerbi_report_spec.md`.

## Prerequisites and local config

1. Copy `.env.example` to `.env` (gitignored) in this folder.
2. Set values for:
   - `DATAVERSE_URL`
   - `FABRIC_WORKSPACE_ID`
   - `FABRIC_WORKSPACE_NAME`
   - `FABRIC_LAKEHOUSE_ID`
   - `FABRIC_LAKEHOUSE_NAME`
3. Select env:
   - PowerShell: `$env:LC_ENV = "ep-10-dataverse-fabriciq"`
4. Set encoding:
   - PowerShell: `$env:PYTHONIOENCODING = "utf-8"`

## Build checklist

### A. Lakehouse substrate (done)
- [x] Confirm Fabric Link Lakehouse + SQL analytics endpoint.
- [x] Create/verify the Fabric Link Delta tables over the Lakehouse.
- [x] Seed native `VendorEnrichment` table (internal performance).
- [x] Seed native `ExternalVendorRisk` table (ProcureIQ external market intelligence).
  - V0001-V0003: match vendors in live launches, with differentiated risk profiles.
  - V0004 (Pacific Rim Components): medium risk, in external DB but not in any Dataverse launch.
  - V0005 (Nexus Cloud Services): critical risk, in external DB but not in any Dataverse launch.
- [x] Seed supplementary native tables via `setup_lakehouse_tables.py`.
- [x] Express the analytics as T-SQL over the Lakehouse SQL endpoint (in the Launch
      Analyst agent): live RED updates, per-blocker vendor context, cross-launch RED
      baseline, and the full 360-degree vendor risk join.

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

### B2. Section 2: measured backfill + replication-latency distribution (done)
- [x] `measure_sync_latency.py`: backfill N tagged status records, poll the OneLake
      mirror with a fresh connection each cycle, and report the write -> OneLake
      latency distribution (min/median/mean/p95/max), an ASCII histogram, a
      matplotlib PNG, and a CSV. Idempotent: `--cleanup` removes every probe record.
- [x] Resolves the SQL analytics endpoint from Fabric REST at runtime (no hardcoded
      identifiers). Detection escapes the `[` in the `[LCSYNC]` tag (T-SQL LIKE and
      Dataverse OData both mishandle a literal leading bracket).

Commands:
```bash
python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --dry-run
python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --apply --count 100
python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --cleanup
```
Note: records written close together replicate in the same Fabric Link micro-batch,
so their measured latencies cluster tightly around the batch cycle time.

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

### E. Section 4: Fabric Cowork plugin (portal step)

The one non-scriptable step. The Fabric plugin is installed by default in
Microsoft 365 Copilot Cowork; it grounds a chat on one Power BI report and the
semantic model behind it, and queries it as the signed-in user (RLS and item
permissions apply). Cowork does not join across models, so the cross-source join
must already live in `Launch Control 360` (built in Section 3). No extra F SKU or
PPU is required beyond what the report already needs.

- [ ] Tenant admin (Fabric admin portal): enable "Share Fabric data with your
      Microsoft 365 services", the cross-region toggle if Fabric and M365 are in
      different regions, and "Users can use the Power BI Model Context Protocol
      server endpoint (preview)".
- [ ] User: Cowork access (M365 Copilot licensing + usage-based Cowork billing) and
      at least Read on the `Launch Control 360` report and its semantic model.
- [ ] In Cowork, ground on the report (attach via the + composer control, paste its
      report link, or reference it by name).
- [ ] Confirm cross-source answers that chain a skill, e.g. "Which launch is most at
      risk once you factor in the vendors behind it?" then "draft an email to the
      launch owner with the vendor, the open ERP exposure, and the recommended
      action." Note: Cowork answers don't cite the source report, so confirm numbers
      in the report before acting.

### F. Final episode proof
- [x] Run RED trigger and confirm Dataverse to Lakehouse SQL timing.
- [ ] Capture proof points:
  - Dataverse write timestamp
  - Lakehouse SQL visibility timestamp (target: <60s)
  - Power BI report refresh showing the new RED update + vendor exposure
  - Fabric answer in Copilot reflecting the same launch
- [x] Add timing summary to `README.md`.

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
- Keep real IDs and URLs in `.env` only. Do not commit environment identifiers.
