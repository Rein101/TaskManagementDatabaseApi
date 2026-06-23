#!/usr/bin/env python3
"""
01_hardened_instructions.py
────────────────────────────
Replaces module_custom_instructions in the semantic view YAML with the most
exhaustive, bulletproof version possible.

WHY THIS EXISTS
Cortex Analyst uses two instruction channels:
  sql_generation        → injected into the SQL-writing prompt
  question_categorization → injected into the intent-classification prompt
Getting these right is the biggest lever for accuracy; they are effectively a
system prompt baked into the semantic layer itself.

USAGE
  python 01_hardened_instructions.py [input.yaml] [output.yaml]
  (defaults: base.yaml → 01_instructions.yaml)
"""

import sys, yaml

SRC = "base.yaml"
OUT = "01_instructions.yaml"

# ═══════════════════════════════════════════════════════════════════════════
# SQL GENERATION INSTRUCTIONS
# Target: ~3 000 chars — concise enough for the token budget, complete enough
# to prevent every known failure mode.
# ═══════════════════════════════════════════════════════════════════════════
SQL_GENERATION = """\
ROLE: OpEx analytics engine for U+4 FP&A reporting (ACT vs FCST / ACT vs Budget).
Fact table: ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX (alias f). Default value column: VAL_EUR_NORM.

━━━ MANDATORY SCOPE FILTERS (always apply — omitting any one corrupts the result) ━━━
  acc.ACCOUNT_LEVEL_1      = 'OPEX'               -- excludes stat/FTE, capex, unmapped
  cc.COST_CENTER_LEVEL_1   = 'All Cost Centers'   -- prevents double-counting sub-nodes
  ent.ENTITY_LEVEL_1       = 'Worldwide'           -- prevents regional sub-total overlap
  pc.PROFIT_CENTER_LEVEL_1 = 'All Profit Center'
  fa.FUNC_AREA_LEVEL_1     = 'Internal Reporting'
Override only when the user explicitly names a different value for one of these fields.

━━━ VERSION RULES — THE SINGLE MOST CRITICAL RULE ━━━
NEVER query without a VERSION filter. NEVER SUM across multiple VERSION values in one row.
  Actual:   f.VERSION = 'Actual'
  Budget:   f.VERSION = 'Budget X'
  Forecast: ALWAYS resolve dynamically — NEVER hardcode strings like 'FY26 FCST P07':
    WITH latest_fcst AS (
      SELECT MAX(VERSION) AS fcst_version
      FROM ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX
      WHERE VERSION ILIKE 'FY% FCST P%'
    )
    Filter: f.VERSION IN ('Actual', (SELECT fcst_version FROM latest_fcst))
    Join:   CROSS JOIN latest_fcst lf  then reference lf.fcst_version

  ACT vs FCST column template (use exactly this pattern):
    SUM(CASE WHEN f.VERSION='Actual'        THEN f.VAL_EUR_NORM ELSE 0 END) AS ACTUAL_EUR,
    SUM(CASE WHEN f.VERSION=lf.fcst_version THEN f.VAL_EUR_NORM ELSE 0 END) AS FORECAST_EUR,
    ROUND(ACTUAL_EUR - FORECAST_EUR, 2)                                      AS VARIANCE_EUR,
    ROUND((ACTUAL_EUR - FORECAST_EUR)/NULLIF(FORECAST_EUR,0)*100, 1)         AS VARIANCE_PCT

  ACT vs Budget column template:
    SUM(CASE WHEN f.VERSION='Actual'   THEN f.VAL_EUR_NORM ELSE 0 END) AS ACTUAL_EUR,
    SUM(CASE WHEN f.VERSION='Budget X' THEN f.VAL_EUR_NORM ELSE 0 END) AS BUDGET_EUR,
    ROUND(ACTUAL_EUR - BUDGET_EUR, 2)                                   AS VARIANCE_EUR,
    ROUND((ACTUAL_EUR - BUDGET_EUR)/NULLIF(BUDGET_EUR,0)*100, 1)        AS VARIANCE_PCT

━━━ FISCAL YEAR — NEVER HARDCODE YEAR LITERALS ━━━
FY starts October, ends September (FY2026 = 2025-10 through 2026-09).
Standard dynamic-bounds CTE (include in every FY-scoped query):
  WITH fy_bounds AS (
    SELECT
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())   ELSE YEAR(CURRENT_DATE())-1 END ||'-10' AS fy_start,
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())+1) ELSE YEAR(CURRENT_DATE())   END ||'-09' AS fy_end,
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN (YEAR(CURRENT_DATE())-1) ELSE YEAR(CURRENT_DATE())-2 END ||'-10' AS pfy_start,
      CASE WHEN MONTH(CURRENT_DATE())>=10 THEN  YEAR(CURRENT_DATE())   ELSE YEAR(CURRENT_DATE())-1  END ||'-09' AS pfy_end
  )
Fiscal quarters — join VW_FISCAL_DATE on f.TIME=d.CAL_YEAR_MONTH_NUM for d.FISC_QTR:
  Q1=Oct-Dec  Q2=Jan-Mar  Q3=Apr-Jun  Q4=Jul-Sep
YTD = fy_start through MAX(f.TIME WHERE f.VERSION='Actual' AND f.TIME >= fy_start).

━━━ FTE / HEADCOUNT — NEVER MIX WITH EUR ━━━
FTE is a count, not money. Location: ACCOUNT_LEVEL_1='Statistical Accounts', ACCOUNT_LEVEL_3 ILIKE '%FTE%'.
RULE: Never sum FTE and EUR values in the same column or the same aggregation pass.
Cost-per-FTE: two separate CTEs:
  (1) opex_cost: ACCOUNT_LEVEL_1='OPEX', SUM(VAL_EUR_NORM)
  (2) fte_avg:   stat accounts + FTE filter, AVG of monthly SUM(VAL_EUR_NORM) per group
  Final: opex_cost.total / NULLIF(fte_avg.avg_fte, 0)
FTE is a stock (point-in-time); average across months — do not SUM across months.

━━━ CURRENCY ━━━
Default: VAL_EUR_NORM (additive; use for all standard queries).
USD: VAL_USD_INI (only if user explicitly asks for USD/dollars).
Local currency: VAL_LC — MANDATORY GROUP BY f.CURRENCY; always show CURRENCY in SELECT; NEVER sum VAL_LC across currencies.

━━━ DRILLDOWN HIERARCHY ━━━
"Why" / "explain" / "drivers" / "diagnose" / "detail" → include full hierarchy in SELECT:
  Account:     ACCOUNT_LEVEL_2, ACCOUNT_LEVEL_3, ACCOUNT_LEVEL_4, ACCOUNT_CODE_AND_DESC
  Cost Center: COST_CENTER_LEVEL_2, COST_CENTER_LEVEL_3, COST_CENTER_LEVEL_4, COST_CENTER_CODE_AND_DESC
  Entity:      ENTITY_LEVEL_2, ENTITY_LEVEL_3, ENTITY_LEVEL_4, ENTITY_CODE_AND_DESC

━━━ OUTPUT FORMAT ━━━
ROUND(value,2) on every monetary column. Always show both VARIANCE_EUR and VARIANCE_PCT.
Positive variance = spent MORE than benchmark (unfavorable for cost management).
ORDER BY VARIANCE_EUR DESC (largest unfavorable first) for diagnostics; by value DESC for rankings.
Default LIMIT 50. Large sums: add TO_CHAR(val/1e6,'999,990.00')||' M' as a supplemental column.\
"""

# ═══════════════════════════════════════════════════════════════════════════
# QUESTION CATEGORIZATION INSTRUCTIONS
# ═══════════════════════════════════════════════════════════════════════════
QUESTION_CATEGORIZATION = """\
SCOPE: OpEx cost-center analytics for U+4 ACT vs FCST / ACT vs Budget reporting.
Covers OPEX and Statistical (FTE/headcount) accounts by cost center, profit center,
entity, functional area, and period. The data source is a Jedox-sourced planning view.

PERIOD DEFAULTS (when user does not specify):
  None stated      → current fiscal year (Oct–Sep, computed dynamically)
  "YTD"            → October through the latest closed Actual month in current FY
  "this quarter"   → current fiscal quarter (Q1=Oct-Dec, Q2=Jan-Mar, Q3=Apr-Jun, Q4=Jul-Sep)
  "last month"     → most recently closed Actual month
  "trend"          → last 18 months of Actual data

VERSION DEFAULTS:
  Standalone reporting (no comparison)   → Actual only
  "vs forecast" / "vs FCST" / "ACT vs FCST"   → Actual vs latest FY% FCST P% version
  "vs budget" / "vs plan" / "ACT vs Budget"   → Actual vs 'Budget X'
  Comparison context without explicit version  → Actual vs latest forecast

ANSWERABLE — generate SQL for:
  OPEX totals, trends, period-over-period comparisons at any dimension level
  ACT vs FCST and ACT vs Budget at any granularity (account, CC, entity, profit center)
  FTE and headcount counts and MoM trend (stat accounts — always isolated from EUR figures)
  Compensation, consulting, tech cost, contractor, travel and entertainment analysis
  Cross-charges (account name pattern match — always note this requires account code verification)
  Local-currency views, cost-per-FTE, budget utilization rates, run rates, YoY/QoQ/MoM

AMBIGUOUS — ask for clarification when:
  A team or cost center name could match multiple records
  Period is at a fiscal quarter boundary (first/last week of a quarter)
  The user asks for "forecast" but implies a specific prior period forecast

OUT OF SCOPE — explain and offer nearest alternative:
  Vendor/supplier names        → offer account-type breakdown (consulting, tech cost, contractor)
  Customer / AR / bad debt     → not in this model; no alternative available
  Revenue / bookings / sales   → not in this model
  Install base / product data  → not in this model
  Gross hires or terminations  → offer net FTE MoM change as a proxy indicator
  Invoice or PO level detail   → not in this model

SIMULATION / WHAT-IF → return the building-block data (run rate, cost-per-FTE, etc.),
state the assumption used, and note that the scenario narrative belongs in the app layer.\
"""


# ─── LiteralDumper (same as all other scripts in this suite) ───────────────
class LiteralDumper(yaml.SafeDumper):
    pass

def _str(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

LiteralDumper.add_representer(str, _str)


# ─── main ──────────────────────────────────────────────────────────────────
def apply(src=SRC, out=OUT):
    d = yaml.safe_load(open(src))

    old_sql   = (d.get("module_custom_instructions") or {}).get("sql_generation", "")
    old_cat   = (d.get("module_custom_instructions") or {}).get("question_categorization", "")

    d["module_custom_instructions"] = {
        "sql_generation":        SQL_GENERATION,
        "question_categorization": QUESTION_CATEGORIZATION,
    }

    with open(out, "w") as fh:
        yaml.dump(d, fh, Dumper=LiteralDumper, sort_keys=False, allow_unicode=True, width=10000)

    print(f"[01] hardened instructions written → {out}")
    print(f"     sql_generation:        {len(old_sql):4d} → {len(SQL_GENERATION):4d} chars")
    print(f"     question_categorization:{len(old_cat):4d} → {len(QUESTION_CATEGORIZATION):4d} chars")
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    apply(src, out)
