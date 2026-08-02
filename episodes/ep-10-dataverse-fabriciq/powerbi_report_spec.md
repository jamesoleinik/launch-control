# Launch Control 360: Power BI report + Fabric IQ consumption (Plane 2)

**Role in episode:** Plane 2, the consumption layer. Instead of a capacity-gated
Fabric Data Agent, launch health is consumed through a **Power BI Direct Lake
semantic model** over the Lakehouse, surfaced two ways:

1. A **Power BI report** ("Launch Control 360") for the visual walk-through.
2. The **Fabric IQ** Copilot plugin ("Turn Power BI data into insights"), which
   lets you ask natural-language questions over the *same* semantic model from
   inside Microsoft 365 Copilot / cowork, with no separate agent to build or publish.

> Why the pivot: Fabric Data Agents require a paid F/P SKU. Power BI semantic
> models and Direct Lake run on trial capacity, and Fabric IQ consumes them
> directly. Same unified data, same three sources, no capacity blocker.

---

## Data foundation

Built on `semantic_views.sql` (applied to the Lakehouse SQL analytics endpoint):

| View | Grain | Sources unified |
|------|-------|-----------------|
| `vw_launch_health` | one row per launch | Dataverse launch + status updates |
| `vw_launch_vendor_exposure` | launch x vendor | Dataverse work + **F&O open invoices** + vendor intel |
| `vw_vendor_360` | one row per vendor | internal perf + ProcureIQ risk + F&O master + open balance |
| `vw_red_status_feed` | one row per RED update | Dataverse status updates |
| `vw_watchlist_vendors` | one row per watchlist vendor | ProcureIQ vendors with no Dataverse work |

The tri-source story the user asked for lives in `vw_launch_vendor_exposure`:
**launch data (Dataverse) + invoice state (F&O) + vendor risk (Lakehouse
supplementary)**. Dataverse work items carry `lc_vendorname`, so this fact joins
to vendor risk on `vendor_name`; F&O open-invoice exposure per vendor rolls up in
`vw_vendor_360` (keyed on `accountnum`).

---

## Semantic model (Direct Lake)

Published programmatically by `setup_powerbi_report.py --create-model` (Fabric
REST, TMSL Direct Lake over all seven views). It can also be built by hand: New
semantic model on the Lakehouse SQL endpoint, pick the views.

**Star shape:**

- Fact: `vw_launch_vendor_exposure` (launch x vendor exposure)
- Fact: `vw_red_status_feed` (RED events)
- Dimension: `vw_launch_health` (launch, keyed on `launch_name`)
- Dimension: `vw_vendor_360` (vendor, keyed on `accountnum`; `vendor_name` for joins)

**Relationships:**

- `vw_launch_vendor_exposure[vendor_name]` → `vw_vendor_360[vendor_name]` (many-to-one)
- `vw_red_status_feed[launch_name]` → `vw_launch_health[launch_name]` (many-to-one)

Note: `vw_launch_vendor_exposure` carries `launch_code` (e.g. `WIDGET-Q3`) while
`vw_launch_health` is keyed on the launch display name (e.g. `Q3 Widget Launch`),
so there is no direct code-to-name relationship in the live data; exposure relates
to launches through the vendor dimension.

### DAX measures

```dax
Total Open ERP Exposure = SUM(vw_vendor_360[open_balance_usd])
Dataverse Invoiced      = SUM(vw_launch_vendor_exposure[dataverse_invoiced_amount])
RED Updates             = SUM(vw_launch_health[red_count])
RED Rate %              = AVERAGE(vw_launch_health[red_pct])
Median RED Rate %       = MEDIANX(ALL(vw_launch_health), vw_launch_health[red_pct])
RED Rate vs Median      = [RED Rate %] - [Median RED Rate %]
High-Risk Vendors       =
    CALCULATE(
        DISTINCTCOUNT(vw_vendor_360[accountnum]),
        vw_vendor_360[market_risk_tier] IN { "High", "Critical" }
    )
Overdue Invoices        = SUM(vw_vendor_360[overdue_count])
```

---

## Report pages ("Launch Control 360")

1. **Launch Health**: RED-rate KPI card, `RED Rate vs Median` bar per launch
   (anomaly at a glance), health stacked column (red/amber/green), latest-update
   timeline. Slicer: launch.
2. **Vendor 360**: table on `vw_vendor_360` (credit rating, financial health
   score, market risk tier, on-time %, open disputes, ERP open balance, overdue).
   Conditional formatting: `market_risk_tier` = High/Critical in red.
3. **Launch x Vendor Exposure**: matrix from `vw_launch_vendor_exposure`:
   rows = launch, columns = vendor, values = `Total Open ERP Exposure` and
   `Dataverse Invoiced` side by side (the tri-source money view).
4. **Blind spots**: `vw_watchlist_vendors`: ProcureIQ high-risk vendors with no
   active Dataverse launch. The "no single system could tell you this" moment.

---

## Fabric IQ in Copilot (cowork access)

Once the semantic model is published, wire the **Fabric IQ** plugin (screenshot:
Fabric IQ → MCP servers → Power BI / Power BI (FabricAIHub)):

1. In Copilot, enable the **Fabric IQ** agent/plugin.
2. Point its Power BI MCP server at the **Launch Control 360** semantic model in
   the LaunchControl workspace.
3. Ask in natural language, e.g.:
   - "Which launch has the highest RED rate versus the median?"
   - "Show open ERP invoice exposure for vendors on launch EP11-DEMO-01."
   - "Which high-risk ProcureIQ vendors have no active launch work?"

Fabric IQ answers over the published semantic model, so the "latest" is whatever
Direct Lake reads from the Lakehouse (fed by low-latency Fabric Link, ~11s median).

---

## Build steps (all available on trial capacity)

1. Seed supplementary tables: `setup_lakehouse_tables.py --apply` (already done).
2. Apply the semantic views: `setup_powerbi_report.py --apply-views`
   (or paste `semantic_views.sql` into the Lakehouse SQL query editor).
3. New semantic model (Direct Lake) on the five views; add relationships + DAX above.
4. Build the four report pages; publish to the LaunchControl workspace.
5. Enable Fabric IQ in Copilot and connect it to the semantic model.
6. Validate: run `trigger_red_health.py --apply --wait 60`, then confirm the new
   RED update appears in the report and in a Fabric IQ answer.

## Relationship to the Fabric Data Agent path

The connected-agent path (`analyst_agent_instructions.md`,
`setup_fabric_data_agent.py`) remains documented as the **upgrade** for when the
workspace moves to F/P capacity. Both paths read the same Lakehouse; this Power
BI + Fabric IQ path is the capacity-free way to ship the episode today.
