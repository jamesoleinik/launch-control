---
name: dataverse-fabric-analytics
description: |
  Teaches how to stand up the analytical layer for a Dataverse solution on
  Microsoft Fabric, and drives an agent to build a named slice of it against a
  live tenant. Fabric is used as the analytical platform: mirror the operational
  Dataverse (and F&O) tables into OneLake, enrich them with related datasets, and
  build top-level aggregation metrics (including historical / cross-record trends)
  that the transactional store does not compute.

  Use whenever the user asks to "mirror Dataverse to Fabric", "measure the Fabric
  Link sync latency", "build a Power BI semantic model / Direct Lake model over the
  Lakehouse", "author the enrichment views", "generate a Power BI report from code
  (no DAX)", or "ground Copilot Cowork on a Fabric report". The calling prompt names
  the SLICE to build; the how lives here. Supported slices:
    - fabric-link   : select the operational tables into Link to Microsoft Fabric so
                      they mirror to the workspace OneLake / Lakehouse SQL endpoint.
    - latency-probe : backfill tagged rows and time Dataverse-write -> OneLake to the
                      second; emit stats + a bucketed distribution graph.
    - analytics     : author the T-SQL enrichment + aggregation views, publish the
                      Direct Lake model and the report via the Fabric REST API, all
                      programmatically (no Power BI Desktop, no hand-written DAX).
    - cowork        : ground Microsoft 365 Copilot Cowork on the one report.
license: MIT
metadata:
  author: Launch Control
  version: "1.0"
---

# Skill: Dataverse analytical layer on Microsoft Fabric

This skill is the knowledge layer for putting an analytical plane on top of a
Dataverse system of record using **Microsoft Fabric** (the platform: Link to
Microsoft Fabric, OneLake, the Lakehouse SQL analytics endpoint, Power BI Direct
Lake, and the Fabric data plugin in Copilot Cowork). It is *not* Fabric IQ. The
prompts that use it can stay short: the *how* lives here, the *what* (the slice
plus its targets) comes in the prompt.

## Why Fabric, not another Dataverse table

Dataverse is the transactional system of record: the live state of **one** launch,
a row you query, relate, secure, and transact. Fabric is the **analytical** plane.
Its job is the work a transactional store should not do:

1. **Enrich.** Join the operational tables to *related* datasets that do not belong
   in Dataverse (internal delivery-performance history, external market/vendor risk,
   the ERP open-invoice ledger).
2. **Aggregate.** Compute top-level metrics **across every record and over time**:
   a launch's RED rate versus the portfolio median, open ERP exposure rolled up per
   launch, historical trend of health. These are cross-record and historical, so
   they live where the analytics engine and the full history live, not on a row.

The boundary test: *would this naturally be a single row I query, relate, secure, or
transact?* Yes -> Dataverse. No, it is cross-record / multi-source / historical
aggregation -> Fabric.

## Conventions (all slices)

- **Auth:** `az login` (the scripts use `AzureCliCredential`). Set
  `LC_ENV=<env>` and `PYTHONIOENCODING=utf-8`.
- **Never hardcode identifiers.** Resolve the Fabric workspace, lakehouse, and the
  SQL analytics endpoint from config / the Fabric REST API at runtime
  (`properties.sqlEndpointProperties.connectionString`); the database is the
  lakehouse name.
- **Idempotent + dry-run.** Every build step is safe to re-run: views are
  `CREATE OR ALTER`, model/report publish via `updateDefinition`, seeds are
  re-run-safe with a `--cleanup`, and each apply supports `--dry-run`.
- Prereqs: `pip install pyodbc azure-identity` + ODBC Driver 18 for SQL Server.

## Slice: fabric-link (mirror the tables)

Link to Microsoft Fabric replicates chosen Dataverse tables into the workspace
OneLake as Delta, with a SQL analytics endpoint over them, in near real time and no
ETL. It is a maker action (Power Apps portal -> Tables -> **Analyze -> Link to
Microsoft Fabric**), not a script:

1. Select the Fabric-entitled environment, pick the target workspace.
2. Select the tables to mirror; each needs **change tracking** (the portal enables
   it on add). Include the operational launch tables and any F&O mirror tables the
   analytics will read.
3. Create the link. Fabric provisions a Lakehouse and does the initial sync; writes
   then replicate continuously.

Verify by querying a mirrored table over the SQL endpoint (or run the latency probe,
which writes a row and watches it land). The first analytics `--apply-views` also
proves the mirror is present.

## Slice: latency-probe (measure the sync)

Backfill a batch of tagged rows through the Dataverse Web API, stamp each with its
write time, then poll the Lakehouse SQL endpoint until each tagged row appears and
record the write-to-OneLake latency to the second. Support `--count` per batch and
`--batches` to repeat so each batch lands in its own replication window; print
min / median / mean / p95 / max plus a histogram, and save a bucketed distribution
graph (x-axis = latency buckets, y-axis = number of syncs) + a CSV. Provide
`--cleanup` (delete every tagged row) and `--dry-run`.

Three gotchas the probe must handle:

- **Reconnect fresh each poll.** A long-lived pyodbc session on the Fabric SQL
  endpoint stays pinned to a stale snapshot and never sees new rows.
- **T-SQL `LIKE` treats `[` as a character class.** A tag like `[LCSYNC]` needs
  `LIKE '![LCSYNC]%' ESCAPE '!'`.
- **OData `startswith` on a leading `[` returns nothing.** Match with
  `contains(<title>,'LCSYNC')` on the Dataverse side.

## Slice: analytics (enrichment views + Direct Lake model + report, no DAX)

The coding agent authors the whole consumption layer via the Fabric REST API; there
is no Power BI Desktop and no hand-written DAX.

### 1. Enrichment + aggregation views (T-SQL, `CREATE OR ALTER`)

Author views on the Lakehouse SQL endpoint that (a) fuse the mirrored operational
tables with the enrichment datasets and (b) roll up the top-level, cross-record and
historical aggregation metrics. Two kinds:

- **Enrichment datasets** are the related, non-operational sources joined in. Where a
  native Delta table is not available, inline them as `VALUES` views for portability,
  and key their names to the operational rows so the joins light up.
- **Aggregation views** compute the metrics a row cannot: per-record rates vs the
  portfolio median, rolled-up exposure, historical health trend, a ranked scorecard
  with a plain-language recommended action.

Key the operational and analytical rows on a stable business key; add a small bridge
view if one source uses a short code and another the display name.

### 2. Direct Lake semantic model (TMSL via Fabric REST)

Introspect the live view columns, build a Direct Lake partition per view, define the
fact-to-dimension relationships (many-to-one, single direction) so the sources
cross-filter, and generate the aggregation **measures** (for example a rate vs the
portfolio median, total open exposure, high-risk counts, overdue counts). Publish
with `compatibilityLevel` 1604; idempotent via `updateDefinition`.

### 3. Power BI report (PBIR via Fabric REST)

Publish a multi-page report `byConnection`, bound to the model. A useful shape: one
decision page (a ranked scorecard with the aggregation metrics), one roster page
(every entity in one enriched row + the blind-spots the operational store cannot
see), and one filtered deep-dive page driven by a slicer. Verify with a DAX
`executeQueries` against the model and by confirming the report `datasetId` matches.

## Slice: cowork (ground Copilot on the report)

The Fabric data plugin in **Microsoft 365 Copilot Cowork** grounds a chat on **one**
Power BI report and the model behind it, and queries it **as the user** (item
permissions and row-level security apply). Cowork does not join across models, so the
whole enriched + aggregated join must already live inside the one model. Enablement:
tenant admin turns on **Share Fabric data with your Microsoft 365 services** (+ the
cross-region toggle if needed) and the **Power BI MCP server endpoint (preview)**;
the user needs Cowork access and at least **Read** on the report and model. Ground on
the report (attach with **+**, paste its link, or name it), then ask a cross-source /
aggregation question and chain the answer into an email, a doc, or a review. Cowork
answers do not cite the source report today, so confirm numbers before acting.
