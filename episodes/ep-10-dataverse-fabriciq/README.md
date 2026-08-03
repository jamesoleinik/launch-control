# Episode 10: Dataverse + Fabric IQ (two-plane AI architecture)

**Status:** ✍️ Draft · 🎬 Not yet recorded
**Build status:** Fabric Link, latency probe, semantic model, 3-page report, and demo data all built programmatically against the live tenant; the Fabric Cowork grounding (Section 4) is the only maker-portal step (2026-08-02)
**Season:** 2 (Dataverse, Better Together)
**Features:** ⭐ Fabric IQ (semantic data layer + Copilot plugin over Microsoft Fabric) · ⭐ Dataverse Link to Microsoft Fabric (near-real-time mirror) · ⭐ Power BI Direct Lake semantic model over the Lakehouse SQL endpoint · ⭐ Fabric IQ in Microsoft 365 Copilot Cowork
**Layer:** 🔵 Layer 2 (proactive automation) over a semantic data foundation
**Coding agent:** Python automation (Dataverse Web API + Fabric REST API: TMSL model + PBIR report) against the live tenant
**Runtime showcased:** the **programmatic Direct Lake + Fabric IQ** consumption plane (the coding agent authors the views, model, relationships, and measures via T-SQL / TMSL / PBIR: no Power BI Desktop authoring and no hand-written DAX)

> **Building this episode?** This README is the follow-along: each section has the
> exact prompt you give the coding agent (or the maker-portal steps you take) and
> what you run on screen. `plan.md` is the deeper build runbook and
> `powerbi_report_spec.md` is the semantic model + report spec.

---

## The hook

> *"Dataverse knows the state of this one launch. Fabric IQ knows what 'normal'
> looks like across every launch we have ever run, and what the external risk
> data says about the vendors involved. This report reasons over all three."*

The Web IQ episode reached outside the tenant for live signal. This one stays
inside but reaches up a level: from individual rows to the semantic meaning of
the data across sources, surfaced in a Power BI report and in Microsoft 365
Copilot through the Fabric IQ plugin.

## Why this is a complement, not a duplicate (the design rule)

The boundary test: *would this naturally be a row I query, relate, secure, or
transact?*

- **Yes -> Dataverse.** The live transactional state of a single launch.
- **No, it is analytical / cross-entity / multi-source -> Fabric IQ.** Trends
  across all launches, external risk intelligence, ERP financial exposure.

The clearest signal is the **Vendor List** page's blind-spot table: Pacific Rim
Components (V0004) and Nexus Cloud Services (V0005) exist only in the ProcureIQ
risk data. Dataverse has never heard of them. Fabric can surface their risk
profile before they ever appear in an operational record.

## The surface: a Power BI report and a Fabric IQ plugin

Instead of a chat agent, the consumption surface here is a governed **semantic
model** with two faces: a Power BI report for the human, and the Fabric IQ plugin
for Microsoft 365 Copilot Cowork. Both read the same Direct Lake model, so the
same cross-source joins answer a click or a prompt.

### The headline result

> *"Which launch is most at risk once you factor in the vendors behind it?"*

1. **Dataverse (Plane 1)** owns the live state: a Copilot Studio agent writes an
   `lc_statusupdate` (health = RED) the moment a launch slips.
2. **Fabric Link** mirrors that row to the Lakehouse in seconds (measured median
   ~46s, Section 2), where the semantic views fuse it with internal delivery
   performance, ProcureIQ market risk, and the F&O open-invoice ledger.
3. **The model synthesizes:** the Q3 Widget Launch is not just RED on status; the
   vendor behind its blocked task (Contoso Supply Co) also carries open ERP
   exposure and a soft ProcureIQ risk tier. One launch, three sources, one row.

Neither plane produces that alone. Dataverse does not hold the ERP ledger or the
market risk; the report does not hold the live transactional write. The semantic
model is the join.

## The two-plane architecture

```
User prompt
    |
[Plane 1: Copilot Studio "Launch Control" agent]
    |  Dataverse MCP: writes lc_statusupdate (health=RED=10600603)
    |
    v  low-latency Fabric Link (measured median ~46s over 1000 writes, Section 2)
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
    |    vw_launch_health, vw_launch_scorecard, vw_vendor_360,
    |    vw_launch_vendor_exposure, vw_red_status_feed, vw_watchlist_vendors,
    |    vw_vendor_enrichment, vw_vendor_risk  (the enrichment dataset),
    |    vw_launch_code_map  (bridge: launch code -> launch name)
    |
    v
[Plane 2: Power BI Direct Lake semantic model "Launch Control 360"]
    |    8 tables + relationships (fact -> dimension) + DAX measures
    |
    +--> Power BI report (3 pages): Launch 360 / Vendor List / Vendor 360
    |
    +--> Fabric IQ plugin in Microsoft 365 Copilot Cowork (grounds on the report)
```

## The build: four sections

The build is one continuous arc. Sections 2 and 3 are authored by a coding agent
from a single prompt each; Sections 1 and 4 are short maker-portal steps because
the Fabric Link and the Cowork grounding are not scriptable.

```
Section 1  Fabric Link   ->  mirror the lc_* and vend* tables to OneLake (maker portal)
Section 2  Backfill+probe->  measure the Dataverse -> OneLake sync latency, graph it (coding agent)
Section 3  Model+report  ->  T-SQL views + Direct Lake model + 3-page report, no DAX (coding agent)
Section 4  Cowork        ->  ground Microsoft 365 Copilot Cowork on the one report (maker portal)
```

> **Local config.** Copy `.env.example` in this folder to `.env` (gitignored) and
> fill in `FABRIC_WORKSPACE_ID`, `FABRIC_WORKSPACE_NAME`, `FABRIC_LAKEHOUSE_ID`,
> `FABRIC_LAKEHOUSE_NAME`, `DATAVERSE_URL`. Select it with
> `LC_ENV=ep-10-dataverse-fabriciq` and set `PYTHONIOENCODING=utf-8`.

## Setup (before Section 1)

This episode needs a **Fabric-entitled** environment: a Dataverse environment with
the `lc_*` launch tables (built in the earlier episodes) plus the F&O `vend*`
mirror tables (Episode 9), and a Microsoft Fabric workspace on capacity to host the
Link, the semantic model, and the report.

1. **Sign in** as the Fabric-entitled account: `az login` (the scripts use
   `AzureCliCredential`). Set `LC_ENV=ep-10-dataverse-fabriciq` and
   `PYTHONIOENCODING=utf-8`.
2. **Python prerequisites:** `pip install pyodbc azure-identity` plus the **ODBC
   Driver 18 for SQL Server** (the probe and the view-apply step connect to the
   Lakehouse SQL analytics endpoint over TDS).
3. **Dataverse MCP server** (for the Plane 1 write in the headline demo): register
   it once with the `dv-connect` skill, exactly as in Episode 9. It is not required
   to build the report, only to demo the live RED write on camera.

The section-by-section build below assumes this is done.

## Section 1 · Create the Fabric Link (mirror the tables to OneLake)

Section 1 stands up the mirror everything else reads: **Link to Microsoft Fabric**
replicates the chosen Dataverse tables into the workspace's OneLake as Delta, with a
SQL analytics endpoint over them, in near real time and with no ETL. This is a maker
action in the Power Apps portal, not a script.

### What the maker does

1. In the **Power Apps maker portal** (`make.powerapps.com`), select the
   Fabric-entitled environment, then open **Tables** and choose **Analyze -> Link to
   Microsoft Fabric**.
2. Pick the target **Fabric workspace** (the one whose ids you put in `.env`).
3. **Select the tables** to mirror. For this episode: the launch tables
   `lc_launch`, `lc_task`, `lc_statusupdate`, `lc_vendorwork`, `lc_milestone`,
   `lc_teammember`, and the F&O mirror tables `vendtable` and `vendtransopen`. Each
   selected table must have **change tracking** enabled (the portal enables it when
   you add the table).
4. **Create the link.** Fabric provisions a Lakehouse in the workspace and does the
   initial sync; after that, writes replicate continuously.

### What you verify

The link is healthy when the tables appear in the Lakehouse SQL analytics endpoint.
The Section 3 view-apply step (`--apply-views`) is the first real consumer; if the
views compile, the mirror is present. A quick manual check is to query one mirrored
table over the SQL endpoint, or run the Section 2 probe, which writes a row and
watches it land.

> **One table is intentionally left out.** `lc_erpsignal` (change-tracking enabled)
> is **not** in the Link's selected set; the current model does not need it. To add
> it later: the maker portal -> the table -> **Analyze -> Link to Microsoft Fabric ->
> Manage tables**, then fold it into a new view.

## Section 2 · Backfill history and measure the sync latency

Section 2 answers the question the "near real time" claim always raises: *how near?*
It backfills a batch of historical launch-status rows, times how long each takes to
appear in OneLake to the second, and graphs the distribution. This is a coding-agent
build.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Section 2 part of this episode's README and write me a self-contained*
> *probe that measures how fast Link to Microsoft Fabric replicates a Dataverse write*
> *into OneLake. Backfill a batch of tagged `lc_statusupdate` rows through the*
> *Dataverse Web API, stamp each with its write time, then poll the Lakehouse SQL*
> *analytics endpoint until each tagged row appears and record the write-to-OneLake*
> *latency to the second. Support `--count` per batch and `--batches` to repeat so*
> *each batch lands in its own replication window; print min / median / mean / p95 /*
> *max plus an ASCII histogram, and save a distribution graph (x-axis = latency*
> *buckets, y-axis = number of syncs) and a CSV. Make it idempotent: a `--cleanup`*
> *that deletes every tagged row and a `--dry-run`. Resolve the SQL endpoint and*
> *lakehouse from config; never hardcode them.*

Three gotchas the agent must handle (they are why the probe reconnects and escapes
the tag), so call them out if it misses them:

- **Reconnect fresh each poll.** A long-lived pyodbc session on the Fabric SQL
  analytics endpoint stays pinned to a stale snapshot and never sees the new rows.
- **T-SQL `LIKE` treats `[` as a character class.** The tag `[LCSYNC]` needs
  `LIKE '![LCSYNC]%' ESCAPE '!'`.
- **OData `startswith` on a leading `[` returns nothing.** Match the tag with
  `contains(lc_title,'LCSYNC')` on the Dataverse side.

### What the agent produces

| Artifact | Where it lands |
|---|---|
| The latency probe (`--apply --count N --batches M`, `--cleanup`, `--dry-run`) | `measure_sync_latency.py` |
| Distribution graph + CSV (gitignored raw outputs) | `sync_latency_hist.png` / `.csv` |
| Committed distribution graph (this doc's asset) | `assets/sync-latency-distribution.png` |

### What you run on screen

```bash
$env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-10-dataverse-fabriciq"
# One batch of 100 (quick demo):
python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --apply --count 100
# The full run: 10 batches of 100, each in its own replication window:
python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --apply --count 100 --batches 10
# Clean up every tagged row when done:
python episodes/ep-10-dataverse-fabriciq/measure_sync_latency.py --cleanup
```

### The measured distribution

Measured over **1000 records** (10 batches of 100) against `eppcdemo1fno`:

| Metric | Value |
|--------|-------|
| Min | 12.0 seconds |
| Median | 45.7 seconds |
| Mean | 45.8 seconds |
| P95 | 65.6 seconds |
| Max | 73.8 seconds |

![Fabric Link sync-latency distribution: 1000 Dataverse writes, x-axis latency buckets, y-axis number of syncs](assets/sync-latency-distribution.png)

The distribution is roughly bell-shaped and centered in the 35-65s range. Records
written close together within a single batch replicate in the same Fabric Link
micro-batch, so per-batch medians vary (here 25-58s) around the tenant's cycle time;
the 1000-record aggregate smooths those into the distribution above. The takeaway for
the demo: a RED status write is queryable in the report in well under two minutes,
typically under one.

## Section 3 · The semantic model and report, from a coding agent (no DAX)

Section 3 builds the entire consumption layer programmatically: the T-SQL views that
fuse the sources, the Direct Lake semantic model over them, and the 3-page report,
all via the Fabric REST API. No Power BI Desktop, and no hand-written DAX; the coding
agent generates the model, relationships, and measures itself.

### The prompt

Type this into GitHub Copilot CLI:

> *Read the Section 3 part of this episode's README and build the whole Power BI*
> *consumption layer for me programmatically against the live tenant, with no Power BI*
> *Desktop and no hand-written DAX. First author a set of T-SQL views on the Fabric*
> *Link Lakehouse SQL endpoint that fuse the Dataverse launch and vendor rows with the*
> *F&O `vendtable` / `vendtransopen` ERP mirror and an enrichment dataset (internal*
> *delivery performance + ProcureIQ market risk), keyed so a launch can see the vendors*
> *behind it and so ProcureIQ-only vendors surface as blind spots. Then generate a*
> *Direct Lake semantic model over those views via the Fabric REST API (TMSL):*
> *introspect the live view columns, build a Direct Lake partition per view, define the*
> *fact-to-dimension relationships, and add the measures (RED rate vs median, open ERP*
> *exposure, high-risk vendors, overdue invoices). Then generate a 3-page report via*
> *PBIR bound to that model: a Launch 360 scorecard page, a Vendor List page, and a*
> *slicer-filtered Vendor 360 page. Make every step idempotent and give me a*
> *`--verify` that proves the report binds to the model.*

### What the agent produces

| Artifact | Where it lands |
|---|---|
| 9 T-SQL views (`CREATE OR ALTER`, idempotent) | `semantic_views.sql` |
| Apply-views + create-model + create-report driver | `setup_powerbi_report.py` |
| Connected demo data (varied RED/AMBER/GREEN + vendor work) | `seed_report_demo.py` |
| Model + report spec, measures, gotchas | `powerbi_report_spec.md` |

### What you run on screen

```bash
$env:PYTHONIOENCODING="utf-8"; $env:LC_ENV="ep-10-dataverse-fabriciq"
# 1. Apply the semantic views to the Lakehouse SQL endpoint.
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views
# 2. Seed richer, connected demo data into Dataverse (idempotent); allow replication.
python episodes/ep-10-dataverse-fabriciq/seed_report_demo.py --apply
# 3. Publish the Direct Lake semantic model (with relationships).
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-model
# 4. Publish the 3-page report bound to the model.
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --create-report
# 5. List the published items and get their ids for the URL.
python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --verify
```

The report opens at
`https://app.powerbi.com/groups/{workspace-id}/reports/{report-id}` and the model at
`.../groups/{workspace-id}/datasets/{model-id}/details`; run `--verify` to get the
ids. Preview any step with `--dry-run`, print the views with `--print-views`, and
remove the demo data with `seed_report_demo.py --cleanup`.

### The semantic layer (`semantic_views.sql`)

Grounded in the live Fabric Link schema (health codes: RED = 10600603,
AMBER = 10600602, GREEN = 10600601):

| View | Grain | Sources unified |
|------|-------|-----------------|
| `vw_launch_health` | one row per launch | Dataverse launch + status updates (RED rate roll-up), keyed on `launch_name` |
| `vw_launch_scorecard` | one row per launch (ranked) | the decision view: current health + latest reason + riskiest vendor + invoiced exposure + `risk_score` + `recommended_action` |
| `vw_red_status_feed` | one row per RED update | Dataverse status updates |
| `vw_launch_vendor_exposure` | launch x vendor work item | Dataverse work + internal ops + ProcureIQ risk, plus `launch_name` via the code map |
| `vw_vendor_360` | one row per vendor | internal perf + ProcureIQ risk + F&O master (`vendtable`) + F&O open balance (`vendtransopen`) |
| `vw_watchlist_vendors` | one row per watchlist vendor | ProcureIQ vendors with no F&O master record |
| `vw_vendor_enrichment` | one row per vendor | internal delivery performance (the enrichment dataset, inline `VALUES`) |
| `vw_vendor_risk` | one row per vendor | ProcureIQ market intelligence (the enrichment dataset, inline `VALUES`) |
| `vw_launch_code_map` | one row per launch | bridge from `lc_vendorwork` launch code to launch display name |

**The enrichment dataset** is the pair `vw_vendor_enrichment` (internal delivery
performance) and `vw_vendor_risk` (ProcureIQ market intelligence). These are the
non-Dataverse, non-ERP source the model joins in; they are inlined as `VALUES` views
for portability (they previously lived in native Delta tables that were lost when the
Lakehouse was recreated), and their vendor names align with the actual `lc_vendorwork`
vendors (Contoso Supply Co, Fabrikam Media, SwiftLogix Freight Co.) so the
cross-source joins light up. They surface in the report on the **Vendor List** and
**Vendor 360** pages (risk tier, delivery score) and in the `risk_score` on the
**Launch 360** scorecard.

Notes on the live data:

- The F&O tables are `vendtable` / `vendtransopen` (no `fno_` prefix).
- `vendtransopen` has no surrogate `Id` column, so invoice counts use `COUNT(*)`.
- `lc_vendorwork` carries a short launch code (for example `WIDGET-Q3`) while the
  rest of the model is keyed on the launch display name (`Q3 Widget Launch`);
  `vw_launch_code_map` bridges the two.

### The Direct Lake model and its relationships

`Launch Control 360` is a Direct Lake model over the 8 analytic views (the code map
is a helper, not a model table). It is a star with two dimensions:

- **Launch dimension:** `vw_launch_health` (keyed on `launch_name`)
- **Vendor dimension:** `vw_vendor_360` (keyed on `accountnum` / `vendor_name`)

Relationships (many-to-one, single direction), so the sources cross-filter:

- `vw_launch_vendor_exposure[vendor_name]` -> `vw_vendor_360[vendor_name]`
- `vw_launch_vendor_exposure[launch_name]` -> `vw_launch_health[launch_name]`
- `vw_red_status_feed[launch_name]` -> `vw_launch_health[launch_name]`
- `vw_watchlist_vendors[accountnum]` -> `vw_vendor_360[accountnum]`

DAX measures (generated by the agent, see `powerbi_report_spec.md`) include
`RED Rate %`, `Median RED Rate %`, `RED Rate vs Median`, `Total Open ERP Exposure`,
`High-Risk Vendors`, and `Overdue Invoices`.

### The report (3 pages)

1. **Launch 360** - the launch decision cockpit. Ranked scorecard
   (`vw_launch_scorecard`): every launch worst-first with its current health,
   riskiest vendor, invoiced exposure, `risk_score`, and a plain-language
   `recommended_action`. KPI cards (RED launches, $ exposure on RED launches,
   launches needing attention, open RED updates), a stacked RED / AMBER / GREEN bar
   per launch, and a risk-score bar.
2. **Vendor List** - the whole vendor roster (`vw_vendor_360`): internal delivery
   performance, ProcureIQ market risk, and the F&O open-invoice ledger in one row,
   with portfolio KPI cards. A second table lists the **blind spots**: ProcureIQ
   risk vendors with no F&O master record (the risk Dataverse alone cannot see).
3. **Vendor 360** - a single-vendor deep dive driven by a vendor slicer. Pick a
   vendor to focus the whole page: its health/perf/exposure cards, its full
   cross-source detail row, and the launches exposed to it (via the model
   relationship on `vendor_name`).

Verified end to end: a DAX `executeQueries` call against the published model returns
rows, and the report `datasetId` matches the model (`--verify`).

## Section 4 · The Fabric Cowork plugin (ground Copilot on the report)

Everything below the Lakehouse is scriptable; the consumption surface in Microsoft
365 Copilot is a maker step. This is the payoff of building a single unified model in
Section 3: the **Fabric IQ plugin** in **Microsoft 365 Copilot Cowork** grounds a
chat on **one** Power BI report and the semantic model behind it, and queries it **as
you** (item permissions and row-level security still apply). Cowork does not join
across models, so the three-source join has to live inside `Launch Control 360`
already. It does, so Cowork can answer across launches, ERP exposure, and vendor risk
from that one report, then chain the answer into an email, a document, or a scheduled
review.

### What the maker does

The Fabric IQ plugin is installed by default in Cowork; no extra F SKU or PPU is
needed beyond what the report already requires.

1. **Tenant admin** (Fabric admin portal): enable **Share Fabric data with your
   Microsoft 365 services**, the **cross-region** toggle if your Fabric and M365
   tenants are in different regions, and **Users can use the Power BI Model Context
   Protocol server endpoint (preview)**.
2. **User**: have Cowork access (Microsoft 365 Copilot licensing + usage-based Cowork
   billing) and at least **Read** on the `Launch Control 360` report and its semantic
   model.
3. In **Cowork**, ground on the report: attach it with the **+** composer control,
   paste its report link, or reference it by name. Then ask.

### The demo prompts

Each starts grounded on the one report, then chains a skill:

- *"Using Launch Control 360, which launch is most at risk once you factor in the
  vendors behind it, and why?"*
- *"For the riskiest launch, draft an email to the launch owner with the vendor, the
  open ERP exposure, and the recommended action."*
- *"Which ProcureIQ high-risk vendors have no active launch work? Turn that into a
  one-page brief."*

> **Caveat for on-camera:** Cowork answers do not cite the source report today, so
> confirm any number against the report before acting on it.

## Pre-record checklist

- [ ] `az login` as the Fabric-entitled account; `LC_ENV=ep-10-dataverse-fabriciq`
      and `PYTHONIOENCODING=utf-8` set.
- [ ] Section 1: Fabric Link created; the 6 `lc_*` and 2 `vend*` tables appear in the
      Lakehouse SQL endpoint.
- [ ] Section 2: the latency probe runs clean and the distribution graph regenerates
      (median ~46s on this tenant).
- [ ] Section 3: `--apply-views` succeeds (all views `CREATE OR ALTER` clean);
      `seed_report_demo.py --apply` run and replication caught up so `vw_launch_health`
      shows a varied RED/AMBER/GREEN mix; `--create-model` and `--create-report` both
      report `[OK]`; `--verify` confirms the report `datasetId` binds to the model.
- [ ] Section 4: Fabric Cowork tenant settings enabled; Cowork grounded on
      `Launch Control 360` with two strong on-camera prompts staged (one cross-source
      question, one chained skill).
- [ ] Confirm the report renders all 3 pages (the Launch 360 scorecard table and the
      Vendor 360 slicer in particular).

## Archived artifacts

These document the original Fabric Data Agent + Operations Agent approach, which was
capacity-gated (Data Agent needs an F/P SKU) and blocked by a Fabric portal UI bug.
Retained for the F/P-capacity upgrade path:

- `setup_fabric_data_agent.py` - Fabric Data Agent portal documentation + verify
- `analyst_agent_instructions.md` - Launch Analyst connected-agent instructions
- `create_analyst_agent.py` - creates the Launch Analyst Copilot Studio agent
  (connected-agent path; needs the Fabric Data Agent first)
- `setup_operations_agent.py`, `operations_agent_*.json` - Operations Agent exports
- `setup_eventhouse.py` - KQL Eventhouse path (evaluated, then archived in favour of
  the Lakehouse SQL endpoint)
- `diagnose_dataactivator_policy.py` - DLP diagnostic for the shared_dataactivator
  blocker

## Cross-references

- **Ep 9:** Dataverse + F&O; the `lc_vendorwork` seam and the `vendtable` /
  `vendtransopen` ERP mirror tables this model reads for financial exposure.
- **Ep 11:** the Web IQ agent (live external signal); this is the internal-semantic
  counterpart.
- **Ep 12:** the Foundry IQ agent (unstructured knowledge); this is the
  structured-semantic counterpart.
- **Ep 13** (convergence): the Fabric IQ story runs alongside Web IQ and Foundry IQ,
  with native Copilot, on one launch.
