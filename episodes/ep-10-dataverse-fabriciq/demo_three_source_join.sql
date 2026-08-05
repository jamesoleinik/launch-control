-- ===========================================================================
-- Episode 10 demo query: three sources, one query, all in Fabric.
--
-- Run this in the Lakehouse SQL analytics endpoint (or a New SQL query) to show
-- the Dataverse launch data, the mirrored F&O vendor data, and the external
-- ProcureIQ market-risk intel joined into a single result grid. Column prefixes
-- make the source of every field obvious on screen:
--   [dv_]  Dataverse   -> lc_vendorwork            (launch vendor work items)
--   [fno_] F&O mirror  -> vendtable + vendtransopen (vendor master + open invoices)
--   [ext_] External    -> vw_vendor_risk           (ProcureIQ market-risk intel)
--
-- The external ProcureIQ view is the bridge: it carries both vendor_name (the
-- Dataverse key) and accountnum (the F&O key), so it stitches the two mirrors
-- together into one per-launch vendor risk picture.
--
-- Prerequisite: vw_vendor_risk must exist. Run the Section 3 views first
-- (--apply-views, which executes semantic_views.sql).
-- ===========================================================================
WITH fno_open AS (          -- aggregate F&O open invoices to the vendor grain
    SELECT accountnum,
           SUM(amountmst)                                                 AS open_balance_usd,
           COUNT(*)                                                       AS open_invoice_count,
           SUM(CASE WHEN duedate < CAST(GETDATE() AS date) THEN 1 ELSE 0 END) AS overdue_count
    FROM vendtransopen
    GROUP BY accountnum
)
SELECT
    -- Dataverse (the launch)
    vw.lc_launchcode              AS dv_launch_code,
    vw.lc_vendorname              AS dv_vendor_name,
    vw.lc_invoicedamount          AS dv_invoiced_amount,
    -- F&O mirror (the ERP vendor + money owed)
    vt.accountnum                 AS fno_account_num,
    vt.blocked                    AS fno_blocked,
    vt.creditmax                  AS fno_credit_limit,
    COALESCE(f.open_balance_usd, 0)   AS fno_open_balance_usd,
    COALESCE(f.overdue_count, 0)      AS fno_overdue_invoices,
    -- External ProcureIQ (the risk profile the launch data can't see)
    evr.credit_rating             AS ext_credit_rating,
    evr.financial_health_score    AS ext_financial_health,
    evr.market_risk_tier          AS ext_market_risk_tier
FROM lc_vendorwork vw
LEFT JOIN vw_vendor_risk evr ON vw.lc_vendorname = evr.vendor_name   -- name  -> account bridge
LEFT JOIN vendtable      vt  ON evr.accountnum   = vt.accountnum      -- into F&O master
LEFT JOIN fno_open       f   ON evr.accountnum   = f.accountnum       -- into F&O open invoices
WHERE (vw.IsDelete = 0 OR vw.IsDelete IS NULL)
ORDER BY
    CASE evr.market_risk_tier
        WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
        WHEN 'Medium'   THEN 2 WHEN 'Low'  THEN 3 ELSE 4 END,
    fno_open_balance_usd DESC;
