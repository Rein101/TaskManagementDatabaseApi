#!/usr/bin/env python3
"""
03_enrich_dimensions.py
────────────────────────
Adds sample_values, is_enum, and supplementary filter-label dimensions to the
semantic view so Cortex Analyst can resolve user inputs precisely without
asking for clarification.

WHY THIS HELPS
  sample_values  → Analyst picks exact column values from user phrasing.
  is_enum:true   → Analyst only ever uses values from the declared list.
  labels:[filter] → marks a boolean expression as a WHERE-clause condition
                    (lets users say "actuals only" or "current FY").

NOTES
  ⚠ Review the TODO markers before deploying — some sample values must be
    confirmed from the actual data (run the audit queries in 06_regression.sql).

USAGE
  python 03_enrich_dimensions.py [input.yaml] [output.yaml]
  (defaults: 02_verified_queries.yaml → 03_enriched.yaml)
"""

import sys, yaml

SRC = "02_verified_queries.yaml"
OUT = "03_enriched.yaml"


# ═══════════════════════════════════════════════════════════════════════════
# ENRICHMENT CATALOGUE
# structure: { table_name: { dim_name: { field: value, ... } } }
# Only keys present in the catalogue are modified; everything else is left.
# ═══════════════════════════════════════════════════════════════════════════
ENRICHMENTS = {

    # ── Fact table ──────────────────────────────────────────────────────
    "VW_JEDOX_DATA_OPEX": {
        "VERSION": {
            # Not is_enum — forecast versions are dynamic (FY% FCST P%).
            # sample_values teaches the model the naming pattern so it
            # can build the ILIKE filter correctly.
            "sample_values": [
                "Actual",
                "Budget X",
                "FY26 FCST P01",
                "FY26 FCST P07",
                # TODO: confirm the current period tag with your planning team
            ],
            "description": (
                "Data version. Core values: 'Actual' (closed accounting), 'Budget X' "
                "(annual plan), and forecast versions matching pattern 'FY## FCST P##' "
                "(e.g. 'FY26 FCST P07'). ALWAYS filter to a specific version — never "
                "aggregate across versions. To get the latest forecast use "
                "MAX(VERSION) WHERE VERSION ILIKE 'FY% FCST P%'."
            ),
        },
        "CURRENCY": {
            # TODO: run SELECT DISTINCT CURRENCY to get the full list
            "is_enum": True,
            "sample_values": ["EUR", "USD", "GBP", "CHF", "PLN", "INR", "SGD"],
            "description": (
                "Transaction currency for VAL_LC. ALWAYS GROUP BY CURRENCY when using "
                "VAL_LC; never sum VAL_LC across currencies. Use VAL_EUR_NORM for all "
                "standard cross-currency aggregations."
            ),
        },
    },

    # ── Account master ──────────────────────────────────────────────────
    "VW_JEDOX_MASTER_DATA_ACCOUNT": {
        "ACCOUNT_LEVEL_1": {
            "is_enum": True,
            "sample_values": [
                "OPEX",
                "Statistical Accounts",
                "Capex Depreciation",
                "Functions Gross Cost excl. ISA",
                "To Be Mapped",
                "All Accounts",
            ],
            "description": (
                "Top account category. 'OPEX' = operating expense money accounts — the "
                "default scope. 'Statistical Accounts' = FTE/headcount counts (NOT money; "
                "never sum with EUR). Filter to 'OPEX' unless the user explicitly asks "
                "for headcount or another category."
            ),
        },
        "ACCOUNT_LEVEL_3": {
            # TODO: run SELECT DISTINCT ACCOUNT_LEVEL_3 WHERE ACCOUNT_LEVEL_1='OPEX'
            # to fill in the complete list; below are the key ones.
            "sample_values": [
                "Compensation",
                "Consulting",
                "Tech Cost",
                "Contractor",
                "Travel and Entertainment",
                "Facilities",
                "Software",
                "Hardware",
                "Training",
                "Marketing",
            ],
            "description": (
                "Cost-type sub-category (3rd level). Key values: 'Compensation' (employee "
                "salaries + benefits), 'Consulting' (external advisory), 'Tech Cost' "
                "(technology spend), 'Contractor' (external headcount), "
                "'Travel and Entertainment' (T&E). Use exact spelling for filtering."
            ),
        },
        "ACCOUNT_LEVEL_1_IS_OPEX": {
            # Convenience boolean filter — marks this as usable in WHERE clauses.
            "_action": "add_new_dimension",
            "name":   "ACCOUNT_LEVEL_1_IS_OPEX",
            "synonyms": ["opex accounts", "operating expense accounts"],
            "description": "TRUE when the account belongs to the OPEX category.",
            "expr":   "ACCOUNT_LEVEL_1 = 'OPEX'",
            "data_type": "BOOLEAN",
            "labels": ["filter"],
        },
        "ACCOUNT_LEVEL_1_IS_STAT": {
            "_action": "add_new_dimension",
            "name":   "ACCOUNT_LEVEL_1_IS_STAT",
            "synonyms": ["statistical accounts", "headcount accounts", "fte accounts"],
            "description": "TRUE when the account is a Statistical Account (FTE/headcount). These are counts, not money.",
            "expr":   "ACCOUNT_LEVEL_1 = 'Statistical Accounts'",
            "data_type": "BOOLEAN",
            "labels": ["filter"],
        },
    },

    # ── Cost center master ───────────────────────────────────────────────
    "VW_JEDOX_MASTER_DATA_COST_CENTER": {
        "COST_CENTER_LEVEL_1": {
            "is_enum": True,
            "sample_values": ["All Cost Centers"],
            "description": (
                "Top-level cost center rollup. Always filter to 'All Cost Centers' "
                "to avoid double-counting when summarizing across the hierarchy."
            ),
        },
        "COST_CENTER_LEVEL_4": {
            # TODO: run SELECT DISTINCT COST_CENTER_LEVEL_4 to get the full list.
            "sample_values": [
                "AMS",
                "EMEA",
                "APAC",
                "Global SVC",
                "Corporate",
                # Add your team names here
            ],
            "description": (
                "Team or sub-team segment at level 4 of the cost center hierarchy. "
                "Common values: 'AMS' (Americas), 'EMEA', 'APAC', 'Global SVC'. "
                "Used for team-level filtering in U+4 reporting."
            ),
        },
    },

    # ── Entity master ────────────────────────────────────────────────────
    "VW_JEDOX_MASTER_DATA_ENTITY": {
        "ENTITY_LEVEL_1": {
            "is_enum": True,
            "sample_values": ["Worldwide"],
            "description": (
                "Top-level entity rollup. Filter to 'Worldwide' to avoid regional "
                "double-counting. Override only when user explicitly asks for a "
                "specific region or country."
            ),
        },
        "ENTITY_LEVEL_2": {
            # TODO: confirm from SELECT DISTINCT ENTITY_LEVEL_2
            "sample_values": ["Americas", "EMEA", "APAC", "Corporate"],
            "description": "Region-level entity grouping (level 2 of entity hierarchy).",
        },
    },

    # ── Functional area master ───────────────────────────────────────────
    "VW_JEDOX_MASTER_DATA_FUNC_AREA": {
        "FUNC_AREA_LEVEL_1": {
            "is_enum": True,
            # TODO: confirm from SELECT DISTINCT FUNC_AREA_LEVEL_1
            "sample_values": [
                "Internal Reporting",
                "Internal Reporting Excluding OIE",
            ],
            "description": (
                "Functional area rollup (level 1). Default: 'Internal Reporting'. "
                "Change to 'Internal Reporting Excluding OIE' only when user asks "
                "to exclude Other Income/Expense items."
            ),
        },
    },

    # ── Profit center master ─────────────────────────────────────────────
    "VW_JEDOX_MASTER_DATA_PROFIT_CENTER": {
        "PROFIT_CENTER_LEVEL_1": {
            "is_enum": True,
            "sample_values": ["All Profit Center"],
            "description": (
                "Top-level profit center rollup. Always filter to 'All Profit Center' "
                "to prevent double-counting."
            ),
        },
    },

    # ── Fiscal date ──────────────────────────────────────────────────────
    "VW_FISCAL_DATE": {
        "FISC_QTR": {
            "is_enum": True,
            "sample_values": ["Q1", "Q2", "Q3", "Q4"],
            "description": (
                "Fiscal quarter. Q1=Oct-Dec, Q2=Jan-Mar, Q3=Apr-Jun, Q4=Jul-Sep. "
                "Requires join on f.TIME = CAL_YEAR_MONTH_NUM."
            ),
        },
    },
}


# ─── LiteralDumper ─────────────────────────────────────────────────────────
class LiteralDumper(yaml.SafeDumper):
    pass

def _str(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

LiteralDumper.add_representer(str, _str)


# ─── helpers ───────────────────────────────────────────────────────────────
def _apply_to_dim(dim, patch):
    """Apply enrichment fields to an existing dimension dict."""
    for k, v in patch.items():
        if k == "_action":
            continue
        dim[k] = v

def _enrich_table(table, table_patches):
    """Apply all patches for one table."""
    for dim_name, patch in table_patches.items():
        action = patch.get("_action")
        if action == "add_new_dimension":
            # Check it doesn't already exist
            existing_names = {d.get("name") for d in table.get("dimensions", [])}
            if patch["name"] not in existing_names:
                new_dim = {k: v for k, v in patch.items() if k != "_action"}
                table.setdefault("dimensions", []).append(new_dim)
        else:
            # Update existing dimension
            for sec in ("dimensions", "time_dimensions", "facts"):
                for dim in table.get(sec, []) or []:
                    if dim.get("name") == dim_name:
                        _apply_to_dim(dim, patch)


# ─── main ──────────────────────────────────────────────────────────────────
def apply(src=SRC, out=OUT):
    d = yaml.safe_load(open(src))
    report = []
    for table in d["tables"]:
        tname = table["name"]
        if tname in ENRICHMENTS:
            _enrich_table(table, ENRICHMENTS[tname])
            report.append(tname)

    with open(out, "w") as fh:
        yaml.dump(d, fh, Dumper=LiteralDumper, sort_keys=False, allow_unicode=True, width=10000)

    print(f"[03] dimension enrichment → {out}")
    print(f"     enriched tables: {', '.join(report)}")
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    apply(src, out)
