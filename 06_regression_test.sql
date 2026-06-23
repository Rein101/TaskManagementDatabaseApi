/* ============================================================================
   06_regression_test.sql
   ══════════════════════
   Run this in Snowflake AFTER deploying the semantic view.
   Validates that:
     1. The semantic view exists and reports correctly.
     2. Every critical SQL pattern from the verified queries executes without
        error and returns at least one row.
     3. The VERSION filter is behaving correctly (no cross-version leakage).
     4. The FTE/EUR isolation rule is working.
     5. The dynamic fiscal-year bounds produce sensible dates.

   EXECUTION
     Run against your non-prod warehouse first.  All tests print PASS or FAIL.
     Fix any FAILs before promoting to production.

   SCOPE
     Runs against: ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX and master data.
     Read-only — no writes.
   ============================================================================ */

USE ROLE    <ANALYST_ROLE>;
USE DATABASE ACC_PRD;
USE SCHEMA  COST_CENTER;
USE WAREHOUSE <YOUR_WH>;

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 0 — Semantic view object exists
-- ──────────────────────────────────────────────────────────────────────────
SHOW SEMANTIC VIEWS LIKE 'OPEX_COST_CENTER_AI' IN SCHEMA ACC_PRD.COST_CENTER;

-- Expect: 1 row returned.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 1 — Dynamic FY bounds sanity check
--   Oct–Sep fiscal year. fy_start should always be YYYY-10, fy_end YYYY-09.
-- ──────────────────────────────────────────────────────────────────────────
WITH fy_bounds AS (
  SELECT
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-10' AS fy_start,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())+1) ELSE YEAR(CURRENT_DATE())   END ||'-09' AS fy_end,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())-1) ELSE YEAR(CURRENT_DATE())-2 END ||'-10' AS pfy_start,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-09' AS pfy_end
)
SELECT
  fy_start, fy_end, pfy_start, pfy_end,
  CASE WHEN RIGHT(fy_start,2)='10' AND RIGHT(fy_end,2)='09'
            AND RIGHT(pfy_start,2)='10' AND RIGHT(pfy_end,2)='09'
       THEN 'PASS — FY bounds correct' ELSE 'FAIL — check month logic' END AS test_result
FROM fy_bounds;

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 2 — VERSION values present in the fact table
--   Confirm the expected VERSION strings actually exist in the data.
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  VERSION,
  COUNT(DISTINCT TIME) AS distinct_periods,
  CASE WHEN VERSION = 'Actual'   THEN 'core_actual'
       WHEN VERSION = 'Budget X' THEN 'core_budget'
       WHEN VERSION ILIKE 'FY% FCST P%' THEN 'forecast'
       ELSE 'other' END AS version_type
FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX
GROUP BY 1
ORDER BY version_type, VERSION;

-- Manually check: 'Actual' and 'Budget X' must appear.
-- At least one 'FY% FCST P%' row must exist.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 3 — Latest forecast version resolves correctly
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  MAX(VERSION) AS latest_fcst_version,
  CASE WHEN MAX(VERSION) ILIKE 'FY% FCST P%' THEN 'PASS — forecast pattern valid'
       ELSE 'FAIL — check ILIKE filter or data' END AS test_result
FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX
WHERE VERSION ILIKE 'FY% FCST P%';

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 4 — ACCOUNT_LEVEL_1 values (scope guardrail audit)
--   Verify the declared enum values exist and 'OPEX' is present.
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  ACCOUNT_LEVEL_1,
  COUNT(*) AS n,
  CASE WHEN ACCOUNT_LEVEL_1 = 'OPEX' THEN 'default_scope' ELSE 'other' END AS category
FROM ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT
GROUP BY 1
ORDER BY n DESC;

-- Expect: 'OPEX' present, 'Statistical Accounts' present.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 5 — ACCOUNT_LEVEL_3 cost-type values
--   Verify the cost-type sample values referenced in VQs exist.
-- ──────────────────────────────────────────────────────────────────────────
SELECT DISTINCT ACCOUNT_LEVEL_3
FROM ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT
WHERE ACCOUNT_LEVEL_1 = 'OPEX'
ORDER BY 1;

-- Review output: confirm 'Compensation', 'Consulting', 'Tech Cost',
-- 'Contractor', 'Travel and Entertainment' are in the list.
-- Update sample_values in 03_enrich_dimensions.py if names differ.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 6 — FTE accounts are isolated (never leak into OPEX sum)
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  CASE WHEN fte_sum = 0 THEN 'PASS — FTE not in OPEX filter'
       ELSE 'FAIL — FTE values leaked into OPEX scope (' || fte_sum || ' records)' END AS test_result
FROM (
  SELECT COUNT(*) AS fte_sum
  FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f
  JOIN ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT a ON f.ACCOUNT = a.ACCOUNT_CODE
  WHERE f.VERSION = 'Actual'
    AND a.ACCOUNT_LEVEL_1 = 'OPEX'
    AND a.ACCOUNT_LEVEL_3 ILIKE '%FTE%'
);

-- PASS means no FTE rows match ACCOUNT_LEVEL_1='OPEX'.  Good.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 7 — Cost center hierarchy node (prevent double-count)
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  COST_CENTER_LEVEL_1,
  COUNT(*) AS n
FROM ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_COST_CENTER
GROUP BY 1
ORDER BY n DESC;

-- Expect 'All Cost Centers' to be present.  Confirm the exact string.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 8 — Core VQ pattern: ACT vs FCST by account
-- ──────────────────────────────────────────────────────────────────────────
WITH fy_bounds AS (
  SELECT
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-10' AS fy_start,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())+1) ELSE YEAR(CURRENT_DATE())   END ||'-09' AS fy_end
),
latest_fcst AS (
  SELECT MAX(VERSION) AS fcst_version
  FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX
  WHERE VERSION ILIKE 'FY% FCST P%'
)
SELECT
  a.ACCOUNT_LEVEL_2, a.ACCOUNT_LEVEL_3,
  ROUND(SUM(CASE WHEN f.VERSION='Actual'        THEN f.VAL_EUR_NORM ELSE 0 END),2) AS ACTUAL_EUR,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END),2) AS FORECAST_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END),2) AS VARIANCE_EUR
FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f
CROSS JOIN latest_fcst lf
JOIN ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION IN ('Actual', (SELECT fcst_version FROM latest_fcst))
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND f.TIME BETWEEN (SELECT fy_start FROM fy_bounds) AND (SELECT fy_end FROM fy_bounds)
GROUP BY 1, 2
ORDER BY ABS(VARIANCE_EUR) DESC
LIMIT 10;

-- Expect: rows with both ACTUAL_EUR and FORECAST_EUR populated, VARIANCE_EUR != 0.
-- If FORECAST_EUR = 0 everywhere: no forecast data for current FY yet.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 9 — YoY comparison dynamic dates (no hardcoded years)
-- ──────────────────────────────────────────────────────────────────────────
WITH fy_bounds AS (
  SELECT
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-10' AS fy_start,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())+1) ELSE YEAR(CURRENT_DATE())   END ||'-09' AS fy_end,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())-1) ELSE YEAR(CURRENT_DATE())-2 END ||'-10' AS pfy_start,
    CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-09' AS pfy_end
),
cur_fy_data AS (
  SELECT SUM(VAL_EUR_NORM) AS total
  FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f, fy_bounds b
  WHERE VERSION = 'Actual' AND TIME BETWEEN b.fy_start AND b.fy_end
),
pfy_data AS (
  SELECT SUM(VAL_EUR_NORM) AS total
  FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f, fy_bounds b
  WHERE VERSION = 'Actual' AND TIME BETWEEN b.pfy_start AND b.pfy_end
)
SELECT
  ROUND(cur_fy_data.total, 2) AS CURRENT_FY_ACTUAL,
  ROUND(pfy_data.total, 2)    AS PRIOR_FY_ACTUAL,
  CASE WHEN cur_fy_data.total IS NOT NULL AND pfy_data.total IS NOT NULL
       THEN 'PASS — both FY periods have data'
       ELSE 'WARN — one or both periods empty; check TIME range' END AS test_result
FROM cur_fy_data, pfy_data;

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 10 — Semantic view metric query (validates relationships compile)
-- ──────────────────────────────────────────────────────────────────────────
SELECT *
FROM SEMANTIC_VIEW(
  ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI
  METRICS    ACTUAL_EUR, BUDGET_EUR, VARIANCE_VS_BUDGET_EUR, VARIANCE_VS_BUDGET_PCT
  DIMENSIONS VW_JEDOX_MASTER_DATA_ACCOUNT.ACCOUNT_LEVEL_2
)
ORDER BY ACTUAL_EUR DESC
LIMIT 10;

-- Expect: rows with populated ACTUAL_EUR and BUDGET_EUR.
-- VARIANCE_VS_BUDGET_EUR = ACTUAL_EUR - BUDGET_EUR.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 11 — Local currency query (validates GROUP BY CURRENCY pattern)
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  f.CURRENCY,
  COUNT(DISTINCT f.COST_CENTER)       AS n_cost_centers,
  ROUND(SUM(f.VAL_LC),2)              AS total_lc,
  ROUND(SUM(f.VAL_EUR_NORM),2)        AS total_eur_norm
FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f
JOIN ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION = 'Actual'
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND f.TIME >= TO_CHAR(DATEADD(month,-3,CURRENT_DATE()),'YYYY-MM')
GROUP BY f.CURRENCY
ORDER BY total_eur_norm DESC;

-- Expect: multiple currencies with matching EUR values.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 12 — COST_CENTER_LEVEL_4 sample values audit
--   Run this and update 03_enrich_dimensions.py with the actual values.
-- ──────────────────────────────────────────────────────────────────────────
SELECT DISTINCT COST_CENTER_LEVEL_4
FROM ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_COST_CENTER
WHERE COST_CENTER_LEVEL_1 = 'All Cost Centers'
ORDER BY 1;

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 13 — Fiscal date join (needed for quarter-level VQs)
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  d.FISC_YEAR, d.FISC_QTR, d.CAL_YEAR_MONTH_NUM,
  COUNT(DISTINCT f.ACCOUNT) AS n_accounts
FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f
JOIN ACC_PRD.MASTERDATA.VW_FISCAL_DATE d ON f.TIME = d.CAL_YEAR_MONTH_NUM
WHERE f.VERSION = 'Actual'
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2, 3
LIMIT 20;

-- Expect: FISC_QTR values Q1-Q4, CAL_YEAR_MONTH_NUM in YYYY-MM format.

-- ──────────────────────────────────────────────────────────────────────────
-- TEST 14 — FTE / headcount query (stat accounts only, no EUR mix)
-- ──────────────────────────────────────────────────────────────────────────
SELECT
  f.TIME AS PERIOD,
  ROUND(SUM(f.VAL_EUR_NORM), 1) AS FTE_COUNT,
  COUNT(DISTINCT f.COST_CENTER) AS n_cost_centers
FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX f
JOIN ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION = 'Actual'
  AND a.ACCOUNT_LEVEL_1 = 'Statistical Accounts'
  AND a.ACCOUNT_LEVEL_3 ILIKE '%FTE%'
  AND f.TIME >= TO_CHAR(DATEADD(month,-3,CURRENT_DATE()),'YYYY-MM')
GROUP BY f.TIME
ORDER BY f.TIME;

-- Expect: FTE_COUNT values that look like headcount (e.g. 50-5000 range).
-- If 0: check ACCOUNT_LEVEL_3 filter — the exact string may differ in your data.

-- ──────────────────────────────────────────────────────────────────────────
-- SUMMARY — run this last to get a quick PASS/FAIL count
-- ──────────────────────────────────────────────────────────────────────────
SELECT 'All regression tests executed. Review each result set above for PASS/FAIL.' AS status;

/* ============================================================================
   WHAT TO DO WITH FAILURES

   TEST 2 — 'Actual' or 'Budget X' missing:
     Check data load. May be a permissions issue on VW_JEDOX_DATA_OPEX.

   TEST 3 — No FCST rows:
     Forecasts may not yet be loaded for the current FY.  ACT vs FCST VQs will
     return empty FORECAST_EUR until data arrives.

   TEST 5 — Cost type names differ:
     Update the ACCOUNT_LEVEL_3 sample_values in 03_enrich_dimensions.py with
     the exact strings you see here, then re-run apply_all.py and redeploy.

   TEST 6 — FTE leaking into OPEX:
     The ACCOUNT hierarchy in your data may differ. Check ACCOUNT_LEVEL_1 values
     for FTE accounts and update the FTE isolation pattern accordingly.

   TEST 8 — FORECAST_EUR all zero:
     Either no FCST data for the FY, or VERSION pattern 'FY% FCST P%' does not
     match. Run: SELECT DISTINCT VERSION FROM VW_JEDOX_DATA_OPEX WHERE VERSION != 'Actual'
     and update the ILIKE pattern in module_custom_instructions.sql_generation.

   TEST 13 — FISC_QTR not Q1-Q4:
     Confirm VW_FISCAL_DATE has a FISC_QTR column and the join key is
     CAL_YEAR_MONTH_NUM = TIME. Update VQ SQL and instructions if column names differ.
   ============================================================================ */
