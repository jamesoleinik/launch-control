-- semantic_views.sql  --  Ep 10 Fabric Lakehouse semantic layer for Power BI.
--
-- These T-SQL views run in the LaunchControl Lakehouse SQL analytics endpoint.
-- They are the "pulled together" semantic layer that a Power BI Direct Lake
-- semantic model consumes. The report (Launch Control 360) and the Fabric IQ
-- Copilot plugin both read the model built on these views, so no Fabric Data
-- Agent (capacity-gated) is required.
--
-- Sources unified here:
--   Dataverse (via Fabric Link):  lc_launch, lc_task, lc_statusupdate, lc_vendorwork
--   F&O ERP  (via Fabric Link):   fno_vendtable (master), fno_vendtransopen (open invoices)
--   Supplementary (seeded):       VendorEnrichment (internal perf), ExternalVendorRisk (ProcureIQ)
--
-- Health codes: RED = 10600603, AMBER = 10600602, GREEN = 10600601.
-- Deleted-row guard on Fabric Link tables: (IsDelete = 0 OR IsDelete IS NULL).
--
-- Apply in the Fabric SQL query editor over the Lakehouse SQL endpoint, or via
--   python episodes/ep-10-dataverse-fabriciq/setup_powerbi_report.py --apply-views
-- Idempotent: every statement is CREATE OR ALTER VIEW.

-- ---------------------------------------------------------------------------
-- vw_launch_health  --  one row per launch: health roll-up + RED rate.
-- Report use: "Launch Health" page, RED-rate KPI, anomaly comparison.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_launch_health AS
SELECT
    l.lc_launchid,
    l.lc_name                                                       AS launch_code,
    l.lc_launchstatus,
    l.lc_targetdate,
    COUNT(su.lc_statusupdateid)                                     AS total_updates,
    SUM(CASE WHEN su.lc_health = 10600603 THEN 1 ELSE 0 END)        AS red_count,
    SUM(CASE WHEN su.lc_health = 10600602 THEN 1 ELSE 0 END)        AS amber_count,
    SUM(CASE WHEN su.lc_health = 10600601 THEN 1 ELSE 0 END)        AS green_count,
    CASE WHEN COUNT(su.lc_statusupdateid) = 0 THEN 0
         ELSE ROUND(100.0 * SUM(CASE WHEN su.lc_health = 10600603 THEN 1 ELSE 0 END)
                    / COUNT(su.lc_statusupdateid), 1)
    END                                                             AS red_pct,
    MAX(su.lc_postedat)                                             AS last_update_at
FROM lc_launch l
LEFT JOIN lc_statusupdate su
       ON su.lc_launchid = l.lc_launchid
      AND (su.IsDelete = 0 OR su.IsDelete IS NULL)
WHERE (l.IsDelete = 0 OR l.IsDelete IS NULL)
GROUP BY l.lc_launchid, l.lc_name, l.lc_launchstatus, l.lc_targetdate;
GO

-- ---------------------------------------------------------------------------
-- vw_vendor_360  --  one row per vendor: internal perf + external (ProcureIQ)
-- risk + ERP master + open-invoice exposure. The cross-source vendor picture.
-- Report use: "Vendor 360" page; slicer/drill on any launch's blocked vendor.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_vendor_360 AS
SELECT
    ve.accountnum,
    ve.vendor_name,
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
FROM VendorEnrichment ve
LEFT JOIN ExternalVendorRisk evr ON ve.accountnum = evr.accountnum
LEFT JOIN fno_vendtable vt       ON ve.accountnum = vt.accountnum
LEFT JOIN (
    SELECT
        accountnum,
        SUM(amountmst)                                              AS open_balance_usd,
        COUNT(Id)                                                   AS open_invoice_count,
        SUM(CASE WHEN duedate < CAST(GETDATE() AS date) THEN 1 ELSE 0 END) AS overdue_count
    FROM fno_vendtransopen
    GROUP BY accountnum
) inv ON ve.accountnum = inv.accountnum;
GO

-- ---------------------------------------------------------------------------
-- vw_launch_vendor_exposure  --  the tri-source fact: for each launch x vendor,
-- the Dataverse work + invoiced amount, the F&O open-invoice state, and the
-- vendor risk intelligence in one row. This is the report's headline grain.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_launch_vendor_exposure AS
SELECT
    l.lc_launchid,
    l.lc_name                                       AS launch_code,
    vw.lc_vendorworkid,
    vw.lc_vendorref                                 AS accountnum,
    ve.vendor_name,
    ve.category,
    vw.lc_invoicedamount                            AS dataverse_invoiced_amount,
    COALESCE(inv.open_balance_usd, 0)               AS erp_open_balance_usd,
    COALESCE(inv.overdue_count, 0)                  AS erp_overdue_count,
    ve.on_time_pct,
    ve.risk_tier                                    AS internal_risk_tier,
    evr.credit_rating,
    evr.financial_health_score,
    evr.market_risk_tier
FROM lc_vendorwork vw
JOIN lc_launch l
      ON l.lc_launchid = vw.lc_launchid
     AND (l.IsDelete = 0 OR l.IsDelete IS NULL)
LEFT JOIN VendorEnrichment ve    ON vw.lc_vendorref = ve.accountnum
LEFT JOIN ExternalVendorRisk evr ON vw.lc_vendorref = evr.accountnum
LEFT JOIN (
    SELECT
        accountnum,
        SUM(amountmst)                                              AS open_balance_usd,
        SUM(CASE WHEN duedate < CAST(GETDATE() AS date) THEN 1 ELSE 0 END) AS overdue_count
    FROM fno_vendtransopen
    GROUP BY accountnum
) inv ON vw.lc_vendorref = inv.accountnum
WHERE (vw.IsDelete = 0 OR vw.IsDelete IS NULL);
GO

-- ---------------------------------------------------------------------------
-- vw_red_status_feed  --  live RED status updates with launch/task context.
-- Report use: "Live RED feed" table visual; Fabric IQ "what just went RED?"
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_red_status_feed AS
SELECT
    su.lc_statusupdateid,
    su.lc_launchidname                              AS launch_code,
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
-- vw_watchlist_vendors  --  ProcureIQ vendors with NO active Dataverse work.
-- The "blind spot" the semantic layer surfaces that no single system shows.
-- ---------------------------------------------------------------------------
CREATE OR ALTER VIEW vw_watchlist_vendors AS
SELECT
    evr.accountnum,
    evr.vendor_name,
    evr.credit_rating,
    evr.financial_health_score,
    evr.market_risk_tier
FROM ExternalVendorRisk evr
WHERE NOT EXISTS (
    SELECT 1 FROM lc_vendorwork vw
    WHERE vw.lc_vendorref = evr.accountnum
      AND (vw.IsDelete = 0 OR vw.IsDelete IS NULL)
);
GO
