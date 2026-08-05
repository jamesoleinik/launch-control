-- ===========================================================================
-- Episode 10 demo query: three sources, one query, all in Fabric.
--
-- Written for the Lakehouse SPARK SQL editor (New Spark SQL query) over the
-- dataverse_<env> Fabric Link lakehouse. It puts three data sources in one grid,
-- with column prefixes so the source of every field is obvious on screen:
--   [dv_]  Dataverse   -> lc_vendorwork            (launch vendor work items)
--   [fno_] F&O mirror  -> vendtable + vendtransopen (vendor master + open invoices)
--   [ext_] External    -> ProcureIQ market-risk intel (inlined below)
--
-- The two mirrored tables (Dataverse + F&O) are real Delta tables Spark reads
-- directly. The external ProcureIQ feed is synthetic, so it is inlined as a
-- VALUES CTE here: that keeps the demo self-contained (no views, no seeding) and
-- makes the "join another dataset to get a risk profile" story explicit. It is
-- the bridge that connects Dataverse (by vendor_name) to F&O (by accountnum).
--
-- Running this on the T-SQL SQL analytics endpoint instead? Swap current_date()
-- for CAST(GETDATE() AS date), and you can replace the ext_procureiq CTE with a
-- join to the vw_vendor_risk view (created by --apply-views).
-- ===========================================================================
WITH ext_procureiq AS (          -- source #3: external ProcureIQ market-risk feed
    SELECT * FROM VALUES
        ('V0001', 'Contoso Supply Co',          'C',  38.0, 'High'),
        ('V0002', 'Fabrikam Media',             'A',  82.0, 'Low'),
        ('V0003', 'SwiftLogix Freight Co.',     'B+', 65.0, 'Medium'),
        ('V0004', 'Pacific Rim Components Ltd.', 'B',  71.0, 'Medium'),
        ('V0005', 'Nexus Cloud Services Inc.',  'C-', 29.0, 'Critical')
    AS t(accountnum, vendor_name, credit_rating, financial_health_score, market_risk_tier)
),
fno_open AS (                    -- source #2: aggregate F&O open invoices to the vendor grain
    SELECT accountnum,
           SUM(amountmst)                                              AS open_balance_usd,
           COUNT(*)                                                    AS open_invoice_count,
           SUM(CASE WHEN duedate < current_date() THEN 1 ELSE 0 END)   AS overdue_count
    FROM vendtransopen
    GROUP BY accountnum
)
SELECT
    -- Dataverse (source #1: the launch)
    vw.lc_launchcode              AS dv_launch_code,
    vw.lc_vendorname              AS dv_vendor_name,
    vw.lc_invoicedamount          AS dv_invoiced_amount,
    -- F&O mirror (source #2: the ERP vendor + money owed)
    vt.accountnum                 AS fno_account_num,
    vt.blocked                    AS fno_blocked,
    vt.creditmax                  AS fno_credit_limit,
    COALESCE(f.open_balance_usd, 0)   AS fno_open_balance_usd,
    COALESCE(f.overdue_count, 0)      AS fno_overdue_invoices,
    -- External ProcureIQ (source #3: the risk profile the launch data can't see)
    evr.credit_rating             AS ext_credit_rating,
    evr.financial_health_score    AS ext_financial_health,
    evr.market_risk_tier          AS ext_market_risk_tier
FROM lc_vendorwork vw
LEFT JOIN ext_procureiq evr ON vw.lc_vendorname = evr.vendor_name   -- name  -> account bridge
LEFT JOIN vendtable     vt  ON evr.accountnum   = vt.accountnum      -- into F&O master
LEFT JOIN fno_open      f   ON evr.accountnum   = f.accountnum       -- into F&O open invoices
WHERE NOT COALESCE(CAST(vw.IsDelete AS BOOLEAN), false)
ORDER BY
    CASE evr.market_risk_tier
        WHEN 'Critical' THEN 0 WHEN 'High' THEN 1
        WHEN 'Medium'   THEN 2 WHEN 'Low'  THEN 3 ELSE 4 END,
    fno_open_balance_usd DESC;
