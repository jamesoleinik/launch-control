-- semantic_views.sql  --  Ep 10 Fabric Lakehouse semantic layer for Power BI.
--
-- These T-SQL views run in the LaunchControl Dataverse Fabric Link lakehouse SQL
-- analytics endpoint. They are the "pulled together" semantic layer that a Power
-- BI Direct Lake semantic model consumes. The report (Launch Control 360) and the
-- Fabric IQ Copilot plugin both read the model built on these views, so no Fabric
-- Data Agent (capacity-gated) is required.
--
-- Grounded in the LIVE schema (verified against the SQL endpoint):
--   Dataverse (via Fabric Link):  lc_launch, lc_task, lc_statusupdate, lc_vendorwork
--   F&O ERP  (via Fabric Link):   vendtable (master), vendtransopen (open invoices)
--   Supplementary demo data:      embedded here as vw_vendor_enrichment /
--                                 vw_vendor_risk (the previously-seeded native
--                                 tables were lost with a recreated lakehouse; the
--                                 data is tiny, so it is inlined for portability).
--
-- Health codes: RED = 10600603, AMBER = 10600602, GREEN = 10600601 (NULL = unset).
-- Deleted-row guard on Fabric Link tables: (IsDelete = 0 OR IsDelete IS NULL).
-- vendtransopen has no surrogate Id column, so invoice counts use COUNT(*).
--
-- Apply via:
--   python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views
-- Idempotent: every statement is CREATE OR ALTER VIEW.

-- ---------------------------------------------------------------------------
-- vw_vendor_enrichment  --  internal delivery performance (was VendorEnrichment).
-- Vendor names align with the Dataverse lc_vendorwork vendors so the cross-source
-- joins light up; accountnum aligns with the F&O vendtable master (V0001-V0003).
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_vendor_enrichment AS
SELECT accountnum, vendor_name, category, on_time_pct, open_disputes, risk_tier
FROM (VALUES
    ('V0001', 'Contoso Supply Co',      'Components',   CAST(0.61 AS float), 2, 'High'),
    ('V0002', 'Fabrikam Media',         'Creative',     CAST(0.88 AS float), 0, 'Low'),
    ('V0003', 'SwiftLogix Freight Co.', 'Logistics',    CAST(0.74 AS float), 1, 'Medium')
) AS t(accountnum, vendor_name, category, on_time_pct, open_disputes, risk_tier);
GO

-- ---------------------------------------------------------------------------
-- vw_vendor_risk  --  external ProcureIQ market intel (was ExternalVendorRisk).
-- V0004/V0005 exist here but not as active F&O/Dataverse vendors (the blind spot).
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_vendor_risk AS
SELECT accountnum, vendor_name, credit_rating, financial_health_score,
       market_risk_tier, diversity_certified, risk_source
FROM (VALUES
    ('V0001', 'Contoso Supply Co',        'C',  CAST(38.0 AS float), 'High',     0, 'ProcureIQ'),
    ('V0002', 'Fabrikam Media',           'A',  CAST(82.0 AS float), 'Low',      1, 'ProcureIQ'),
    ('V0003', 'SwiftLogix Freight Co.',   'B+', CAST(65.0 AS float), 'Medium',   0, 'ProcureIQ'),
    ('V0004', 'Pacific Rim Components Ltd.','B', CAST(71.0 AS float), 'Medium',   1, 'ProcureIQ'),
    ('V0005', 'Nexus Cloud Services Inc.', 'C-', CAST(29.0 AS float), 'Critical', 0, 'ProcureIQ')
) AS t(accountnum, vendor_name, credit_rating, financial_health_score,
       market_risk_tier, diversity_certified, risk_source);
GO

-- ---------------------------------------------------------------------------
-- vw_launch_code_map  --  bridges the lc_vendorwork short launch code to the
-- launch display name used everywhere else, so vendor exposure relates to the
-- launch dimension (vw_launch_health).
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_launch_code_map AS
SELECT launch_code, launch_name
FROM (VALUES
    ('WIDGET-Q3',     'Q3 Widget Launch'),
    ('API-Q2',        'Q2 API Platform Upgrade'),
    ('WHSE-Q3',       'Q3 Warehouse Consolidation'),
    ('VPORTAL-Q2',    'Q2 Vendor Portal Cutover'),
    ('COMPLIANCE-Q3', 'Q3 Compliance Reporting'),
    ('PRICING-Q1',    'Q1 Pricing Refresh')
) AS t(launch_code, launch_name);
GO

-- ---------------------------------------------------------------------------
-- vw_launch_health  --  one row per launch: health roll-up + RED rate.
-- Keyed on lc_launchidname (the launch name carried on each status update), which
-- is the reliable launch grain in the live data.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_launch_health AS
SELECT
    su.lc_launchidname                                              AS launch_name,
    COUNT(*)                                                        AS total_updates,
    SUM(CASE WHEN su.lc_health = 10600603 THEN 1 ELSE 0 END)        AS red_count,
    SUM(CASE WHEN su.lc_health = 10600602 THEN 1 ELSE 0 END)        AS amber_count,
    SUM(CASE WHEN su.lc_health = 10600601 THEN 1 ELSE 0 END)        AS green_count,
    CASE WHEN COUNT(*) = 0 THEN 0
         ELSE ROUND(100.0 * SUM(CASE WHEN su.lc_health = 10600603 THEN 1 ELSE 0 END)
                    / COUNT(*), 1)
    END                                                             AS red_pct,
    MAX(su.lc_postedat)                                             AS last_update_at
FROM lc_statusupdate su
WHERE (su.IsDelete = 0 OR su.IsDelete IS NULL)
  AND su.lc_launchidname IS NOT NULL
GROUP BY su.lc_launchidname;
GO

-- ---------------------------------------------------------------------------
-- vw_vendor_360  --  one row per vendor: internal perf + external (ProcureIQ)
-- risk + F&O master + open-invoice exposure. The cross-source vendor picture.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_vendor_360 AS
SELECT
    COALESCE(ve.accountnum, evr.accountnum)         AS accountnum,
    COALESCE(ve.vendor_name, evr.vendor_name)       AS vendor_name,
    ve.category,
    ve.on_time_pct,
    ve.open_disputes,
    ve.risk_tier                                    AS internal_risk_tier,
    evr.credit_rating,
    evr.financial_health_score,
    evr.market_risk_tier,
    evr.diversity_certified,
    vt.blocked                                      AS erp_blocked,
    vt.creditmax                                    AS erp_credit_limit,
    COALESCE(inv.open_balance_usd, 0)               AS open_balance_usd,
    COALESCE(inv.open_invoice_count, 0)             AS open_invoice_count,
    COALESCE(inv.overdue_count, 0)                  AS overdue_count
FROM vw_vendor_risk evr
FULL OUTER JOIN vw_vendor_enrichment ve ON evr.accountnum = ve.accountnum
LEFT JOIN vendtable vt ON COALESCE(ve.accountnum, evr.accountnum) = vt.accountnum
LEFT JOIN (
    SELECT
        accountnum,
        SUM(amountmst)                                              AS open_balance_usd,
        COUNT(*)                                                    AS open_invoice_count,
        SUM(CASE WHEN duedate < CAST(GETDATE() AS date) THEN 1 ELSE 0 END) AS overdue_count
    FROM vendtransopen
    GROUP BY accountnum
) inv ON COALESCE(ve.accountnum, evr.accountnum) = inv.accountnum;
GO

-- ---------------------------------------------------------------------------
-- vw_launch_vendor_exposure  --  per launch x vendor work item: the Dataverse
-- invoiced amount joined to vendor risk intelligence (by vendor name, the key
-- that connects lc_vendorwork to the enrichment data in the live environment).
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_launch_vendor_exposure AS
SELECT
    vw.lc_launchcode                                AS launch_code,
    lcm.launch_name                                 AS launch_name,
    vw.lc_vendorname                                AS vendor_name,
    vw.lc_invoicedamount                            AS dataverse_invoiced_amount,
    vw.lc_committedamount                           AS dataverse_committed_amount,
    ve.on_time_pct,
    ve.risk_tier                                    AS internal_risk_tier,
    evr.credit_rating,
    evr.financial_health_score,
    evr.market_risk_tier
FROM lc_vendorwork vw
LEFT JOIN vw_launch_code_map lcm    ON vw.lc_launchcode = lcm.launch_code
LEFT JOIN vw_vendor_enrichment ve   ON vw.lc_vendorname = ve.vendor_name
LEFT JOIN vw_vendor_risk evr        ON vw.lc_vendorname = evr.vendor_name
WHERE (vw.IsDelete = 0 OR vw.IsDelete IS NULL);
GO

-- ---------------------------------------------------------------------------
-- vw_red_status_feed  --  live RED status updates with launch/task context.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_red_status_feed AS
SELECT
    su.lc_statusupdateid,
    su.lc_launchidname                              AS launch_name,
    su.lc_taskidname                                AS task_title,
    su.lc_title,
    su.lc_summary,
    su.lc_postedat,
    su.createdon
FROM lc_statusupdate su
WHERE su.lc_health = 10600603
  AND (su.IsDelete = 0 OR su.IsDelete IS NULL);
GO

-- ---------------------------------------------------------------------------
-- vw_watchlist_vendors  --  ProcureIQ vendors with NO active F&O vendor master
-- record. The "blind spot" the semantic layer surfaces (V0004 / V0005).
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_watchlist_vendors AS
SELECT
    evr.accountnum,
    evr.vendor_name,
    evr.credit_rating,
    evr.financial_health_score,
    evr.market_risk_tier
FROM vw_vendor_risk evr
WHERE NOT EXISTS (
    SELECT 1 FROM vendtable vt WHERE vt.accountnum = evr.accountnum
);
GO
