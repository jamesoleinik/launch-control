# Episode 10: Dataverse + Fabric IQ (two-plane AI architecture)

**Status:** Semantic model + report built programmatically. Fabric IQ Copilot wiring is the only manual step remaining. Not yet recorded.

**Season:** 2 (Dataverse, Better Together)
**Features:** Fabric IQ (semantic data layer + Copilot plugin over Microsoft Fabric) · Dataverse MCP Server (transactional state) · Power BI Direct Lake semantic model (over the Lakehouse SQL endpoint) · Fabric Data Agent (optional upgrade on F/P capacity)
**Layer:** Layer 2 (proactive automation) over a semantic data foundation
**Runtime:** Copilot Studio (Plane 1) + Dataverse MCP + Fabric Link + Lakehouse SQL + Power BI Direct Lake + Fabric IQ (Plane 2)

> **Building this episode?** `plan.md` is the self-contained build runbook.
> `powerbi_report_spec.md` is the semantic model + report spec. This README
> documents what has actually been built and how to reproduce it.

---

## The hook

> *"Dataverse knows the state of this one launch. Fabric IQ knows what 'normal'
> looks like across every launch we have ever run, and what the external risk
> data says about the vendors involved. This report reasons over all three."*

The Web IQ episode reached outside the tenant for live signal. This one stays
inside but reaches up a level: from individual rows to the semantic meaning of
the data across sources, surfaced in a Power BI report and in Microsoft 365
Copilot through the Fabric IQ plugin.

## What is built (this pass)

Everything below the Lakehouse is created programmatically against the live
tenant. No manual Power BI Desktop authoring.

1. **Semantic layer** (`semantic_views.sql`): 8 T-SQL views on the LaunchControl
   Dataverse Fabric Link Lakehouse SQL analytics endpoint. Applied with
   `setup_powerbi_report.py --apply-views` (idempotent, every view is
   `CREATE OR ALTER`).
2. **Direct Lake semantic model** `Launch Control 360`: published via the Fabric
   REST API (TMSL, `compatibilityLevel 1604`) with
   `setup_powerbi_report.py --create-model`. Introspects the live view columns,
   builds Direct Lake partitions over each view, and defines the cross-source
   relationships. Idempotent via `updateDefinition`.
3. **Power BI report** `Launch Control 360`: a 5-page report published via the
   Fabric REST API (PBIR, `definition.pbir` `byConnection`) with
   `setup_powerbi_report.py --create-report`, bound to the model. Idempotent.
4. **Demo data**: `seed_report_demo.py` writes a varied RED/AMBER/GREEN status
   mix across all launches plus vendor work items spread across launches, so the
   report tells the cross-source story. Idempotent (re-run safe) with `--cleanup`.

Verified end to end: a DAX `executeQueries` call against the published model
returns rows, and the report `datasetId` matches the model.

## The two-plane architecture

```
User prompt
    |
[Plane 1: Copilot Studio "Launch Control" agent]
    |  Dataverse MCP: writes lc_statusupdate (health=RED=10600603)
    |
    v  low-latency Fabric Link (median ~11s)
[LaunchControl Dataverse Fabric Link Lakehouse - SQL analytics endpoint]
    |
    |  Dataverse mirror tables:
    |    lc_launch, lc_task, lc_statusupdate, lc_vendorwork, lc_milestone,
    |    lc_teammember
    |  F&O ERP mirror tables:
    |    vendtable (vendor master), vendtransopen (open invoices)
    |
    v
[Semantic layer: semantic_views.sql]
    |    vw_launch_health, vw_vendor_360, vw_launch_vendor_exposure,
    |    vw_red_status_feed, vw_watchlist_vendors,
    |    vw_vendor_enrichment, vw_vendor_risk  (inline supplementary data),
    |    vw_launch_code_map  (bridge: launch code -> launch name)
    |
    v
[Plane 2: Power BI Direct Lake semantic model "Launch Control 360"]
    |    7 tables + relationships (fact -> dimension) + DAX measures
    |
    +--> Power BI report (5 pages): Launch Health / Vendor 360 /
    |    Launch x Vendor Exposure / Cross-Source 360 / Blind Spots
    |
    +--> Fabric IQ plugin in Microsoft 365 Copilot (Power BI MCP server):
         "Which launch's RED rate is most anomalous vs. the median?"
         "Open ERP invoice exposure for vendors on the Q3 Widget Launch?"
         "Which high-risk ProcureIQ vendors have no active launch work?"
```

## The semantic layer (`semantic_views.sql`)

Grounded in the live Fabric Link schema (health codes: RED = 10600603,
AMBER = 10600602, GREEN = 10600601):

| View | Grain | Sources unified |
|------|-------|-----------------|
| `vw_launch_health` | one row per launch | Dataverse launch + status updates (RED rate roll-up), keyed on `launch_name` |
| `vw_red_status_feed` | one row per RED update | Dataverse status updates |
| `vw_launch_vendor_exposure` | launch x vendor work item | Dataverse work + internal ops + ProcureIQ risk, plus `launch_name` via the code map |
| `vw_vendor_360` | one row per vendor | internal perf + ProcureIQ risk + F&O master (`vendtable`) + F&O open balance (`vendtransopen`) |
| `vw_watchlist_vendors` | one row per watchlist vendor | ProcureIQ vendors with no F&O master record |
| `vw_vendor_enrichment` | one row per vendor | internal delivery performance (inline `VALUES`) |
| `vw_vendor_risk` | one row per vendor | ProcureIQ market intelligence (inline `VALUES`) |
| `vw_launch_code_map` | one row per launch | bridge from `lc_vendorwork` launch code to launch display name |

Notes on the live data:

- The F&O tables are `vendtable` / `vendtransopen` (no `fno_` prefix).
- `vendtransopen` has no surrogate `Id` column, so invoice counts use `COUNT(*)`.
- Vendor enrichment / ProcureIQ risk previously lived in native Delta tables that
  were lost when the Lakehouse was recreated. They are now inlined as
  `vw_vendor_enrichment` / `vw_vendor_risk` `VALUES` views for portability, and
  their vendor names align with the actual `lc_vendorwork` vendors (Contoso Supply
  Co, Fabrikam Media, SwiftLogix Freight Co.) so the cross-source joins light up.
- `lc_vendorwork` carries a short launch code (for example `WIDGET-Q3`) while the
  rest of the model is keyed on the launch display name (`Q3 Widget Launch`).
  `vw_launch_code_map` bridges the two.

## The Direct Lake model and its relationships

`Launch Control 360` is a Direct Lake model over the 7 analytic views (the code
map is a helper, not a model table). It is a star with two dimensions:

- **Launch dimension:** `vw_launch_health` (keyed on `launch_name`)
- **Vendor dimension:** `vw_vendor_360` (keyed on `accountnum` / `vendor_name`)

Relationships (many-to-one, single direction), so the sources cross-filter:

- `vw_launch_vendor_exposure[vendor_name]` -> `vw_vendor_360[vendor_name]`
- `vw_launch_vendor_exposure[launch_name]` -> `vw_launch_health[launch_name]`
- `vw_red_status_feed[launch_name]` -> `vw_launch_health[launch_name]`
- `vw_watchlist_vendors[accountnum]` -> `vw_vendor_360[accountnum]`

DAX measures (see `powerbi_report_spec.md`) include `RED Rate %`,
`Median RED Rate %`, `RED Rate vs Median`, `Total Open ERP Exposure`,
`High-Risk Vendors`, and `Overdue Invoices`.

## The report (5 pages)

1. **Launch Health** - executive overview: launch-count / RED / AMBER / total-update
   KPI cards, a stacked RED / AMBER / GREEN bar per launch (fixed RAG colors), and a
   launch health table.
2. **Vendor 360** - open-balance and overdue cards, full vendor risk/exposure
   table (internal + ProcureIQ + F&O in one row).
3. **Launch x Vendor Exposure** - Dataverse invoiced/committed per launch x vendor
   with internal and market risk tiers.
4. **Cross-Source 360** - a single matrix that unifies Dataverse launch/work,
   internal delivery ops, and ProcureIQ market risk, with the F&O vendor ledger
   alongside. This is the "multiple datasets coming together" view.
5. **Blind Spots** - ProcureIQ watchlist vendors with no F&O master record
   (the risk Dataverse alone cannot see).

## Why this is a complement, not a duplicate (the design rule)

The boundary test: *would this naturally be a row I query, relate, secure, or
transact?*

- **Yes -> Dataverse.** The live transactional state of a single launch.
- **No, it is analytical / cross-entity / multi-source -> Fabric IQ.** Trends
  across all launches, external risk intelligence, ERP financial exposure.

The clearest signal is the **Blind Spots** page: Pacific Rim Components (V0004)
and Nexus Cloud Services (V0005) exist only in the ProcureIQ risk data. Dataverse
has never heard of them. Fabric can surface their risk profile before they ever
appear in an operational record.

## Build steps (reproduce)

> **Local config.** Copy `.env.example` to `.env` (gitignored) and fill in your
> values: `FABRIC_WORKSPACE_ID`, `FABRIC_WORKSPACE_NAME`, `FABRIC_LAKEHOUSE_ID`,
> `FABRIC_LAKEHOUSE_NAME`, `DATAVERSE_URL`. Select the env with
> `LC_ENV=ep-10-dataverse-fabriciq` and set `PYTHONIOENCODING=utf-8`.
> Auth is `az login` (AzureCliCredential).
>
> Prerequisites: `pip install pyodbc azure-identity` plus the ODBC Driver 18 for
> SQL Server.

```bash
# 1. Apply the semantic views to the Lakehouse SQL endpoint.
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views

# 2. Seed richer, connected demo data into Dataverse (idempotent).
python episodes/ep-10-dataverse-fabriciq/seed_report_demo.py --apply
#    Allow ~60s (occasionally several minutes) for Fabric Link replication.

# 3. Publish the Direct Lake semantic model (with relationships).
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model

# 4. Publish the 5-page report bound to the model.
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-report

# 5. List the published items (and get their ids for the URL).
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --verify
```

The report opens at
`https://app.powerbi.com/groups/{workspace-id}/reports/{report-id}` and the model
at `.../groups/{workspace-id}/datasets/{model-id}/details`; run `--verify` to get
the ids.

Other useful commands:

```bash
# Preview without applying:
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model --dry-run
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-report --dry-run

# Print the views / the report+Fabric IQ build steps:
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --print-views
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --instructions

# Remove the seeded demo data:
python episodes/ep-10-dataverse-fabriciq/seed_report_demo.py --cleanup
```

### The one manual step: Fabric IQ in Copilot

Everything else is scriptable. Enabling the Fabric IQ / Copilot plugin (the
Power BI MCP server) in Microsoft 365 Copilot and pointing it at the
`Launch Control 360` model is a UI toggle with no supported API.

## Fabric Link completeness

The Fabric Link mirrors 6 `lc_*` tables plus the `vend*` F&O tables. One Dataverse
table is **not** in the Link's selected table set:

- **`lc_erpsignal`** (change-tracking enabled) is missing from Fabric Link. To add
  it: maker portal -> the table -> Analyze -> Link to Microsoft Fabric ->
  Manage tables. It is not required by the current model; fold it into a view once
  it is available.

## Replication latency (measured, eppcdemo1fno)

| Metric | Value |
|--------|-------|
| Median | ~11 seconds |
| P95 | ~48 seconds |
| E2E (write -> Lakehouse SQL) | ~58 seconds |
| Cold-start / large batch first sync | up to several minutes |

## Archived artifacts

These document the original Fabric Data Agent + Operations Agent approach, which
was capacity-gated (Data Agent needs an F/P SKU) and blocked by a Fabric portal UI
bug. Retained for the F/P-capacity upgrade path:

- `setup_fabric_data_agent.py` - Fabric Data Agent portal documentation + verify
- `analyst_agent_instructions.md` - Launch Analyst connected-agent instructions
- `setup_operations_agent.py`, `operations_agent_*.json` - Operations Agent exports
- `setup_eventhouse.py` - KQL Eventhouse path (evaluated, then archived in favour
  of the Lakehouse SQL endpoint)
- `diagnose_dataactivator_policy.py` - DLP diagnostic for the shared_dataactivator
  blocker

## Cross-references

- **Ep 11:** the Web IQ agent (external signal); this is the internal-semantic
  counterpart.
- **Ep 13** (convergence): the Fabric IQ story runs alongside Web IQ and Foundry
  IQ on one launch.
