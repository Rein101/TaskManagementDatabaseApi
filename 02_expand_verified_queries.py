#!/usr/bin/env python3
"""
02_expand_verified_queries.py
──────────────────────────────
Adds 15 high-quality verified queries (golden examples) covering the full range
of U+4 reporting questions that weren't in the first build pass.

WHY MORE VERIFIED QUERIES BEAT GENIE
Cortex Analyst uses verified queries as few-shot retrieval examples.  More
good examples = the model finds a close match for almost any phrasing the user
tries, then adapts the pattern.  Genie has zero domain-specific examples.
Target: ≥ 40 VQs covering every important question shape before going to prod.

USAGE
  python 02_expand_verified_queries.py [input.yaml] [output.yaml]
  (defaults: 01_instructions.yaml → 02_verified_queries.yaml)
"""

import sys, re, time, yaml

SRC = "01_instructions.yaml"
OUT = "02_verified_queries.yaml"

OPEX = "ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX"
ACCT = "ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT"
CC   = "ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_COST_CENTER"
ENT  = "ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ENTITY"
PC   = "ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_PROFIT_CENTER"
FA   = "ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_FUNC_AREA"
DATE = "ACC_PRD.MASTERDATA.VW_FISCAL_DATE"

# Dynamic FY bounds CTE (reused in many queries).
FY_BOUNDS = """\
  fy_bounds AS (
    SELECT
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-10' AS fy_start,
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())+1) ELSE YEAR(CURRENT_DATE())   END ||'-09' AS fy_end,
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())-1) ELSE YEAR(CURRENT_DATE())-2 END ||'-10' AS pfy_start,
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-09' AS pfy_end
  )"""

CUR_FY_BETWEEN = (
    "(CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())    ELSE YEAR(CURRENT_DATE())-1 END ||'-10') "
    "AND (CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())+1) ELSE YEAR(CURRENT_DATE())   END ||'-09')"
)

TS = int(time.time())

def vq(question, sql, onboard=False):
    return {
        "name":                     question.strip(),
        "question":                 question.strip(),
        "sql":                      sql.rstrip(),
        "verified_at":              TS,
        "verified_by":              "prompt_engineering_suite_v1",
        "use_as_onboarding_question": onboard,
    }


# ─── 15 new verified queries ────────────────────────────────────────────────
NEW_VQS = [

# 1. ACT vs Budget by profit center (YTD)
vq("Show Actual vs Budget variance by profit center year-to-date.",
f"""WITH
{FY_BOUNDS},
  ytd_end AS (
    SELECT MAX(f.TIME) AS ytd
    FROM {OPEX} f, fy_bounds b
    WHERE f.VERSION = 'Actual' AND f.TIME BETWEEN b.fy_start AND b.fy_end
  )
SELECT
  p.PROFIT_CENTER_LEVEL_2, p.PROFIT_CENTER_LEVEL_3, p.PROFIT_CENTER_CODE_AND_DESC AS PROFIT_CENTER,
  ROUND(SUM(CASE WHEN f.VERSION='Actual'   THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS ACTUAL_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS BUDGET_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS VARIANCE_EUR,
  ROUND((SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END))
    / NULLIF(SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 0) * 100, 1) AS VARIANCE_PCT
FROM {OPEX} f
CROSS JOIN ytd_end
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {PC} p ON f.PROFIT_CENTER = p.PROFIT_CENTER_CODE
WHERE f.VERSION IN ('Actual', 'Budget X')
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND p.PROFIT_CENTER_LEVEL_1 = 'All Profit Center'
  AND f.TIME BETWEEN (SELECT fy_start FROM fy_bounds) AND ytd_end.ytd
GROUP BY 1, 2, 3
HAVING ABS(VARIANCE_EUR) > 0
ORDER BY VARIANCE_EUR DESC"""),

# 2. Q-over-Q progression within current FY (all four quarters)
vq("Show OPEX by fiscal quarter for the current fiscal year — Q1 through Q4 progression.",
f"""WITH cur AS (
  SELECT CASE WHEN MONTH(CURRENT_DATE())>=10 THEN YEAR(CURRENT_DATE())+1 ELSE YEAR(CURRENT_DATE()) END AS fy
)
SELECT
  a.ACCOUNT_LEVEL_2, a.ACCOUNT_LEVEL_3,
  SUM(CASE WHEN d.FISC_QTR='Q1' THEN f.VAL_EUR_NORM ELSE 0 END) AS Q1_EUR,
  SUM(CASE WHEN d.FISC_QTR='Q2' THEN f.VAL_EUR_NORM ELSE 0 END) AS Q2_EUR,
  SUM(CASE WHEN d.FISC_QTR='Q3' THEN f.VAL_EUR_NORM ELSE 0 END) AS Q3_EUR,
  SUM(CASE WHEN d.FISC_QTR='Q4' THEN f.VAL_EUR_NORM ELSE 0 END) AS Q4_EUR,
  ROUND(SUM(f.VAL_EUR_NORM), 2) AS FULL_YEAR_EUR
FROM {OPEX} f
CROSS JOIN cur
JOIN {DATE} d ON f.TIME = d.CAL_YEAR_MONTH_NUM
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION = 'Actual'
  AND d.FISC_YEAR = cur.fy
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
GROUP BY 1, 2
ORDER BY FULL_YEAR_EUR DESC"""),

# 3. Budget utilization YTD — how much of the full-year budget has been consumed
vq("What is the budget utilization rate by cost center? How much of the annual budget has been spent YTD?",
f"""WITH
{FY_BOUNDS},
  ytd_end AS (
    SELECT MAX(f.TIME) AS ytd
    FROM {OPEX} f, fy_bounds b
    WHERE f.VERSION = 'Actual' AND f.TIME BETWEEN b.fy_start AND b.fy_end
  )
SELECT
  c.COST_CENTER_LEVEL_3, c.COST_CENTER_LEVEL_4, c.COST_CENTER_CODE_AND_DESC AS COST_CENTER,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' AND f.TIME <= ytd_end.ytd THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS YTD_ACTUAL,
  ROUND(SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FULL_YEAR_BUDGET,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' AND f.TIME <= ytd_end.ytd THEN f.VAL_EUR_NORM ELSE 0 END)
    / NULLIF(SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 0) * 100, 1) AS UTILIZATION_PCT
FROM {OPEX} f
CROSS JOIN ytd_end
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {CC} c ON f.COST_CENTER = c.COST_CENTER_CODE
WHERE f.VERSION IN ('Actual', 'Budget X')
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND c.COST_CENTER_LEVEL_1 = 'All Cost Centers'
  AND f.TIME BETWEEN (SELECT fy_start FROM fy_bounds) AND (SELECT fy_end FROM fy_bounds)
GROUP BY 1, 2, 3
HAVING FULL_YEAR_BUDGET > 0
ORDER BY UTILIZATION_PCT DESC"""),

# 4. Compensation as % of total OPEX by cost center
vq("What percentage of total OPEX is employee compensation by cost center this fiscal year?",
f"""WITH
  comp AS (
    SELECT f.COST_CENTER, SUM(f.VAL_EUR_NORM) AS comp_eur
    FROM {OPEX} f
    JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
    WHERE f.VERSION = 'Actual'
      AND a.ACCOUNT_LEVEL_1 = 'OPEX'
      AND a.ACCOUNT_LEVEL_3 = 'Compensation'
      AND f.TIME BETWEEN {CUR_FY_BETWEEN}
    GROUP BY f.COST_CENTER
  ),
  total AS (
    SELECT f.COST_CENTER, SUM(f.VAL_EUR_NORM) AS total_eur
    FROM {OPEX} f
    JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
    WHERE f.VERSION = 'Actual'
      AND a.ACCOUNT_LEVEL_1 = 'OPEX'
      AND f.TIME BETWEEN {CUR_FY_BETWEEN}
    GROUP BY f.COST_CENTER
  )
SELECT
  c.COST_CENTER_CODE_AND_DESC AS COST_CENTER,
  ROUND(comp.comp_eur, 2)   AS COMPENSATION_EUR,
  ROUND(total.total_eur, 2) AS TOTAL_OPEX_EUR,
  ROUND(comp.comp_eur / NULLIF(total.total_eur, 0) * 100, 1) AS COMP_PCT_OF_OPEX
FROM comp
JOIN total ON comp.COST_CENTER = total.COST_CENTER
JOIN {CC} c ON comp.COST_CENTER = c.COST_CENTER_CODE
ORDER BY COMP_PCT_OF_OPEX DESC"""),

# 5. Controllable spend (OPEX excluding compensation)
vq("Show controllable (non-compensation) OPEX by cost center and account type this fiscal year.",
f"""SELECT
  c.COST_CENTER_LEVEL_3, c.COST_CENTER_LEVEL_4, c.COST_CENTER_CODE_AND_DESC AS COST_CENTER,
  a.ACCOUNT_LEVEL_3 AS COST_TYPE,
  ROUND(SUM(f.VAL_EUR_NORM), 2) AS CONTROLLABLE_EUR
FROM {OPEX} f
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {CC} c ON f.COST_CENTER = c.COST_CENTER_CODE
WHERE f.VERSION = 'Actual'
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND a.ACCOUNT_LEVEL_3 != 'Compensation'
  AND c.COST_CENTER_LEVEL_1 = 'All Cost Centers'
  AND f.TIME BETWEEN {CUR_FY_BETWEEN}
GROUP BY 1, 2, 3, 4
ORDER BY CONTROLLABLE_EUR DESC"""),

# 6. 3-month run rate vs full-year budget (pace tracking)
vq("What is the annualized run rate based on the last 3 months of Actual vs the annual budget by cost center?",
f"""WITH
{FY_BOUNDS},
  last3_months AS (
    SELECT DISTINCT TIME FROM {OPEX}
    WHERE VERSION = 'Actual'
      AND TIME >= TO_CHAR(DATEADD(month, -3, CURRENT_DATE()), 'YYYY-MM')
    ORDER BY TIME DESC
    LIMIT 3
  ),
  run_rate AS (
    SELECT f.COST_CENTER,
      SUM(f.VAL_EUR_NORM) / NULLIF(COUNT(DISTINCT f.TIME), 0) * 12 AS annualized_eur
    FROM {OPEX} f
    WHERE f.VERSION = 'Actual' AND f.TIME IN (SELECT TIME FROM last3_months)
    GROUP BY f.COST_CENTER
  ),
  budget AS (
    SELECT f.COST_CENTER, SUM(f.VAL_EUR_NORM) AS budget_eur
    FROM {OPEX} f
    JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
    WHERE f.VERSION = 'Budget X'
      AND a.ACCOUNT_LEVEL_1 = 'OPEX'
      AND f.TIME BETWEEN (SELECT fy_start FROM fy_bounds) AND (SELECT fy_end FROM fy_bounds)
    GROUP BY f.COST_CENTER
  )
SELECT
  c.COST_CENTER_CODE_AND_DESC AS COST_CENTER,
  ROUND(run_rate.annualized_eur, 2)  AS ANNUALIZED_RUN_RATE_EUR,
  ROUND(budget.budget_eur, 2)        AS ANNUAL_BUDGET_EUR,
  ROUND(run_rate.annualized_eur - budget.budget_eur, 2) AS PACE_VARIANCE_EUR,
  ROUND((run_rate.annualized_eur - budget.budget_eur) / NULLIF(budget.budget_eur, 0) * 100, 1) AS PACE_VARIANCE_PCT
FROM run_rate
JOIN budget ON run_rate.COST_CENTER = budget.COST_CENTER
JOIN {CC} c ON run_rate.COST_CENTER = c.COST_CENTER_CODE
WHERE c.COST_CENTER_LEVEL_1 = 'All Cost Centers'
ORDER BY PACE_VARIANCE_EUR DESC"""),

# 7. Exception list: cost centers over forecast by >10%
vq("Which cost centers are over forecast by more than 10 percent this fiscal year?",
f"""WITH latest_fcst AS (
  SELECT MAX(VERSION) AS fcst_version FROM {OPEX} WHERE VERSION ILIKE 'FY% FCST P%'
)
SELECT
  c.COST_CENTER_LEVEL_3, c.COST_CENTER_LEVEL_4, c.COST_CENTER_CODE_AND_DESC AS COST_CENTER,
  ROUND(SUM(CASE WHEN f.VERSION='Actual'        THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS ACTUAL_EUR,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FORECAST_EUR,
  ROUND((SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END))
    / NULLIF(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 0) * 100, 1) AS OVER_FCST_PCT
FROM {OPEX} f
CROSS JOIN latest_fcst lf
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {CC} c ON f.COST_CENTER = c.COST_CENTER_CODE
WHERE f.VERSION IN ('Actual', (SELECT fcst_version FROM latest_fcst))
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND c.COST_CENTER_LEVEL_1 = 'All Cost Centers'
  AND f.TIME BETWEEN {CUR_FY_BETWEEN}
GROUP BY 1, 2, 3
HAVING OVER_FCST_PCT > 10
ORDER BY OVER_FCST_PCT DESC"""),

# 8. Top 5 accounts by absolute ACT vs FCST variance (focus list)
vq("What are the top 5 accounts driving the largest Actual vs Forecast variance this fiscal year?",
f"""WITH latest_fcst AS (
  SELECT MAX(VERSION) AS fcst_version FROM {OPEX} WHERE VERSION ILIKE 'FY% FCST P%'
)
SELECT
  a.ACCOUNT_LEVEL_2, a.ACCOUNT_LEVEL_3, a.ACCOUNT_LEVEL_4, a.ACCOUNT_CODE_AND_DESC AS ACCOUNT,
  ROUND(SUM(CASE WHEN f.VERSION='Actual'        THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS ACTUAL_EUR,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FORECAST_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS VARIANCE_EUR,
  ROUND((SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END))
    / NULLIF(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 0)*100,1) AS VARIANCE_PCT
FROM {OPEX} f
CROSS JOIN latest_fcst lf
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION IN ('Actual', (SELECT fcst_version FROM latest_fcst))
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND f.TIME BETWEEN {CUR_FY_BETWEEN}
GROUP BY 1, 2, 3, 4
ORDER BY ABS(VARIANCE_EUR) DESC
LIMIT 5"""),

# 9. 18-month compensation trend by cost center
vq("Show the 18-month compensation spend trend by cost center.",
f"""SELECT
  f.TIME AS PERIOD,
  c.COST_CENTER_LEVEL_4, c.COST_CENTER_CODE_AND_DESC AS COST_CENTER,
  ROUND(SUM(f.VAL_EUR_NORM), 2) AS COMP_EUR
FROM {OPEX} f
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {CC} c ON f.COST_CENTER = c.COST_CENTER_CODE
WHERE f.VERSION = 'Actual'
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND a.ACCOUNT_LEVEL_3 = 'Compensation'
  AND c.COST_CENTER_LEVEL_1 = 'All Cost Centers'
  AND f.TIME >= TO_CHAR(DATEADD(month, -18, CURRENT_DATE()), 'YYYY-MM')
GROUP BY 1, 2, 3
ORDER BY PERIOD, COST_CENTER"""),

# 10. Month-over-month change for last 6 months at account level
vq("Show the month-over-month OPEX change for the last 6 months broken down by account type.",
f"""WITH monthly AS (
  SELECT
    f.TIME, a.ACCOUNT_LEVEL_3 AS COST_TYPE, SUM(f.VAL_EUR_NORM) AS monthly_eur
  FROM {OPEX} f
  JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
  WHERE f.VERSION = 'Actual'
    AND a.ACCOUNT_LEVEL_1 = 'OPEX'
    AND f.TIME >= TO_CHAR(DATEADD(month, -6, CURRENT_DATE()), 'YYYY-MM')
  GROUP BY f.TIME, a.ACCOUNT_LEVEL_3
)
SELECT
  TIME AS PERIOD, COST_TYPE, ROUND(monthly_eur, 2) AS MONTHLY_EUR,
  ROUND(monthly_eur - LAG(monthly_eur) OVER (PARTITION BY COST_TYPE ORDER BY TIME), 2) AS MOM_CHANGE_EUR,
  ROUND((monthly_eur - LAG(monthly_eur) OVER (PARTITION BY COST_TYPE ORDER BY TIME))
    / NULLIF(LAG(monthly_eur) OVER (PARTITION BY COST_TYPE ORDER BY TIME), 0) * 100, 1) AS MOM_CHANGE_PCT
FROM monthly
ORDER BY TIME DESC, ABS(MOM_CHANGE_EUR) DESC NULLS LAST"""),

# 11. FTE headcount by entity/region (stat accounts — never mixed with EUR)
vq("Show FTE headcount by entity and region. How many FTEs are in each region?",
f"""SELECT
  e.ENTITY_LEVEL_2 AS REGION, e.ENTITY_LEVEL_3 AS COUNTRY, e.ENTITY_CODE_AND_DESC AS ENTITY,
  f.TIME AS PERIOD,
  ROUND(SUM(f.VAL_EUR_NORM), 1) AS FTE_COUNT
FROM {OPEX} f
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {ENT} e ON f.ENTITY = e.ENTITY_CODE
WHERE f.VERSION = 'Actual'
  AND a.ACCOUNT_LEVEL_1 = 'Statistical Accounts'
  AND a.ACCOUNT_LEVEL_3 ILIKE '%FTE%'
  AND e.ENTITY_LEVEL_1 = 'Worldwide'
  AND f.TIME BETWEEN {CUR_FY_BETWEEN}
GROUP BY 1, 2, 3, 4
ORDER BY REGION, PERIOD"""),

# 12. ACT vs FCST by entity / region
vq("Show the Actual vs Forecast variance by entity and region this fiscal year.",
f"""WITH latest_fcst AS (
  SELECT MAX(VERSION) AS fcst_version FROM {OPEX} WHERE VERSION ILIKE 'FY% FCST P%'
)
SELECT
  e.ENTITY_LEVEL_2 AS REGION, e.ENTITY_LEVEL_3 AS COUNTRY, e.ENTITY_CODE_AND_DESC AS ENTITY,
  ROUND(SUM(CASE WHEN f.VERSION='Actual'        THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS ACTUAL_EUR,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FORECAST_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS VARIANCE_EUR
FROM {OPEX} f
CROSS JOIN latest_fcst lf
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
JOIN {ENT} e ON f.ENTITY = e.ENTITY_CODE
WHERE f.VERSION IN ('Actual', (SELECT fcst_version FROM latest_fcst))
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND e.ENTITY_LEVEL_1 = 'Worldwide'
  AND f.TIME BETWEEN {CUR_FY_BETWEEN}
GROUP BY 1, 2, 3
HAVING ABS(VARIANCE_EUR) > 0
ORDER BY VARIANCE_EUR DESC"""),

# 13. Same quarter prior year comparison (Q2 this FY vs Q2 last FY)
vq("Compare Q2 this fiscal year vs Q2 last fiscal year by account hierarchy.",
f"""WITH cur AS (
  SELECT CASE WHEN MONTH(CURRENT_DATE())>=10 THEN YEAR(CURRENT_DATE())+1 ELSE YEAR(CURRENT_DATE()) END AS fy
)
SELECT
  a.ACCOUNT_LEVEL_2, a.ACCOUNT_LEVEL_3, a.ACCOUNT_LEVEL_4, a.ACCOUNT_CODE_AND_DESC AS ACCOUNT,
  ROUND(SUM(CASE WHEN d.FISC_YEAR=cur.fy   AND d.FISC_QTR='Q2' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS THIS_Q2,
  ROUND(SUM(CASE WHEN d.FISC_YEAR=cur.fy-1 AND d.FISC_QTR='Q2' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS PRIOR_Q2,
  ROUND(SUM(CASE WHEN d.FISC_YEAR=cur.fy   AND d.FISC_QTR='Q2' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN d.FISC_YEAR=cur.fy-1 AND d.FISC_QTR='Q2' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS VARIANCE_EUR
FROM {OPEX} f
CROSS JOIN cur
JOIN {DATE} d ON f.TIME = d.CAL_YEAR_MONTH_NUM
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION = 'Actual'
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND d.FISC_QTR = 'Q2'
GROUP BY 1, 2, 3, 4
HAVING ABS(VARIANCE_EUR) > 0
ORDER BY VARIANCE_EUR DESC"""),

# 14. Forecast accuracy: for closed months, how accurate was the latest FCST?
vq("How accurate has the forecast been for the months already closed this fiscal year?",
f"""WITH
{FY_BOUNDS},
  latest_fcst AS (
    SELECT MAX(VERSION) AS fcst_version FROM {OPEX} WHERE VERSION ILIKE 'FY% FCST P%'
  ),
  closed_months AS (
    SELECT DISTINCT f.TIME
    FROM {OPEX} f, fy_bounds b
    WHERE f.VERSION = 'Actual' AND f.TIME BETWEEN b.fy_start AND b.fy_end
  )
SELECT
  f.TIME AS PERIOD,
  ROUND(SUM(CASE WHEN f.VERSION='Actual'        THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS ACTUAL_EUR,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS LATEST_FCST_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FCST_ERROR_EUR,
  ROUND((SUM(CASE WHEN f.VERSION='Actual' THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END))
    / NULLIF(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 0)*100,1) AS ERROR_PCT
FROM {OPEX} f
CROSS JOIN latest_fcst lf
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION IN ('Actual', (SELECT fcst_version FROM latest_fcst))
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND f.TIME IN (SELECT TIME FROM closed_months)
GROUP BY f.TIME
ORDER BY f.TIME"""),

# 15. Full-year forecast vs full-year budget — the high-level summary
vq("Compare the full-year forecast to the full-year budget by account category.",
f"""WITH
{FY_BOUNDS},
  latest_fcst AS (
    SELECT MAX(VERSION) AS fcst_version FROM {OPEX} WHERE VERSION ILIKE 'FY% FCST P%'
  )
SELECT
  a.ACCOUNT_LEVEL_2 AS ACCOUNT_CATEGORY, a.ACCOUNT_LEVEL_3 AS ACCOUNT_TYPE,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FULL_YEAR_FORECAST_EUR,
  ROUND(SUM(CASE WHEN f.VERSION='Budget X'       THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS FULL_YEAR_BUDGET_EUR,
  ROUND(SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 2) AS REFORECAST_DELTA_EUR,
  ROUND((SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END)
    - SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END))
    / NULLIF(SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END), 0)*100,1) AS REFORECAST_PCT
FROM {OPEX} f
CROSS JOIN latest_fcst lf
JOIN {ACCT} a ON f.ACCOUNT = a.ACCOUNT_CODE
WHERE f.VERSION IN ((SELECT fcst_version FROM latest_fcst), 'Budget X')
  AND a.ACCOUNT_LEVEL_1 = 'OPEX'
  AND f.TIME BETWEEN (SELECT fy_start FROM fy_bounds) AND (SELECT fy_end FROM fy_bounds)
GROUP BY 1, 2
HAVING ABS(REFORECAST_DELTA_EUR) > 0
ORDER BY ABS(REFORECAST_DELTA_EUR) DESC"""),

]  # end NEW_VQS


# ─── LiteralDumper ─────────────────────────────────────────────────────────
class LiteralDumper(yaml.SafeDumper):
    pass

def _str(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

LiteralDumper.add_representer(str, _str)


# ─── dedup helper ──────────────────────────────────────────────────────────
def _key(q):
    return re.sub(r"\s+", " ", (q.get("question") or "").strip().lower())


# ─── main ──────────────────────────────────────────────────────────────────
def apply(src=SRC, out=OUT):
    d = yaml.safe_load(open(src))
    existing_keys = {_key(q) for q in d.get("verified_queries", [])}
    added = []
    for q in NEW_VQS:
        k = _key(q)
        if k not in existing_keys:
            d["verified_queries"].append(q)
            existing_keys.add(k)
            added.append(q["name"][:70])

    with open(out, "w") as fh:
        yaml.dump(d, fh, Dumper=LiteralDumper, sort_keys=False, allow_unicode=True, width=10000)

    print(f"[02] verified queries → {out}")
    print(f"     added {len(added)} new VQs (total: {len(d['verified_queries'])})")
    for n in added:
        print(f"     + {n}")
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    apply(src, out)
