#!/usr/bin/env python3
"""
apply_all.py
─────────────
Master orchestrator.  Runs the full prompt-engineering pipeline in sequence:

  base.yaml
    → 01_hardened_instructions.py  (bulletproof module_custom_instructions)
    → 02_expand_verified_queries.py (15 more golden VQs, total ~49)
    → 03_enrich_dimensions.py       (sample_values, is_enum, filter labels)
    → opex_final_semantic_view.yaml  (PRODUCTION OUTPUT)

Then validates the result and prints a diff summary.

USAGE
  cd scripts/
  python apply_all.py                        # uses base.yaml as input
  python apply_all.py my_custom_base.yaml    # custom input

OUTPUT
  opex_final_semantic_view.yaml   → deploy to Snowflake
  opex_agent_config.json          → Cortex Agent config (PATH B, optional)
  opex_agent_wrapper.sql          → Agent SQL wrapper (PATH B, optional)

NEXT STEPS AFTER THIS SCRIPT
  1. Review the YAML (spot-check a few VQ SQL blocks).
  2. Deploy with verify-first: CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML('ACC_PRD.COST_CENTER', $$...$$, TRUE)
  3. Run 06_regression_test.sql against Snowflake.
  4. Fix any FAILs (usually sample_values / enum strings that differ in your data).
  5. Redeploy without verify_only flag.
  6. Build the Streamlit app using 05_api_prompt_engineering.py.
"""

import sys, os, yaml

# ─── add scripts dir to path ─────────────────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

import importlib
m01 = importlib.import_module("01_hardened_instructions")
m02 = importlib.import_module("02_expand_verified_queries")
m03 = importlib.import_module("03_enrich_dimensions")
m04 = importlib.import_module("04_cortex_agent_config")

BASE  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCRIPTS_DIR, "base.yaml")
FINAL = os.path.join(SCRIPTS_DIR, "opex_final_semantic_view.yaml")


def _count(d, key):
    return sum(len(t.get(key, []) or []) for t in d["tables"])


def _vq_titles(d):
    return [q.get("name", "")[:70] for q in d.get("verified_queries", [])]


def _validate(path: str) -> dict:
    """Lightweight structural validation of the output YAML."""
    d = yaml.safe_load(open(path))
    errors = []
    warnings = []

    # 1. Valid YAML (safe_load already confirmed that)
    # 2. Name set correctly
    if d.get("name") != "OPEX_COST_CENTER_AI":
        errors.append(f"name is '{d.get('name')}', expected 'OPEX_COST_CENTER_AI'")

    # 3. No EDW_DEV or ACC_DEV anywhere
    raw = open(path).read()
    for bad in ("EDW_DEV", "ACC_DEV"):
        if bad in raw:
            errors.append(f"Stale reference found: '{bad}'")

    # 4. No hardcoded year literals in any VQ SQL
    import re
    for q in d.get("verified_queries", []):
        sql = q.get("sql", "")
        for pattern in ("'2025-10'", "'2026-09'", "'2024-10'", "'2025-09'"):
            if pattern in sql:
                errors.append(f"Hardcoded year in VQ '{q['name'][:50]}': {pattern}")

    # 5. module_custom_instructions present and non-empty
    mci = d.get("module_custom_instructions") or {}
    for key in ("sql_generation", "question_categorization"):
        val = mci.get(key, "")
        if len(val) < 200:
            warnings.append(f"module_custom_instructions.{key} looks too short ({len(val)} chars)")

    # 6. OPEX table has metrics
    opex = next((t for t in d["tables"] if t["name"] == "VW_JEDOX_DATA_OPEX"), None)
    if not opex or not opex.get("metrics"):
        errors.append("VW_JEDOX_DATA_OPEX has no table-level metrics")

    # 7. View-level derived metrics present
    if not d.get("metrics"):
        errors.append("No view-level derived metrics found")

    # 8. Duplicate VQ check
    import re as re2
    def norm(s): return re2.sub(r"\s+", " ", (s or "").strip().lower())
    seen = {}
    for q in d.get("verified_queries", []):
        k = norm(q.get("question"))
        if k in seen:
            errors.append(f"Duplicate VQ question: '{q['name'][:50]}'")
        seen[k] = True

    # 9. FUNC_AREA must be ACC_PRD
    fa = next((t for t in d["tables"] if t["name"] == "VW_JEDOX_MASTER_DATA_FUNC_AREA"), None)
    if fa and fa["base_table"].get("database") != "ACC_PRD":
        errors.append(f"FUNC_AREA still pointing to dev database: {fa['base_table']}")

    # 10. Token budget estimate (without sample_values)
    import copy
    d2 = copy.deepcopy(d)
    for t in d2["tables"]:
        for sec in ("dimensions", "facts", "time_dimensions"):
            for it in t.get(sec, []) or []:
                it.pop("sample_values", None)
    approx_tokens = len(yaml.dump(d2)) // 4
    if approx_tokens > 32_000:
        warnings.append(f"Estimated token budget {approx_tokens:,} exceeds 32K guideline")

    return {
        "errors":   errors,
        "warnings": warnings,
        "vq_count": len(d.get("verified_queries", [])),
        "tokens":   approx_tokens,
        "dims":     _count(d, "dimensions"),
        "facts":    _count(d, "facts"),
        "metrics_table":   sum(len(t.get("metrics",[])or[]) for t in d["tables"]),
        "metrics_view":    len(d.get("metrics", [])),
    }


def main():
    print("=" * 60)
    print("OpEx Semantic View — Prompt Engineering Pipeline")
    print("=" * 60)

    # ── Load baseline stats ──────────────────────────────────────────────
    base_d = yaml.safe_load(open(BASE))
    base_vqs = len(base_d.get("verified_queries", []))
    print(f"\nBase YAML:  {BASE}")
    print(f"  VQs:      {base_vqs}")
    print(f"  Dims:     {_count(base_d, 'dimensions')}")

    # ── Run the pipeline ─────────────────────────────────────────────────
    print("\n── Running pipeline ────────────────────────────────────────")
    p01 = m01.apply(BASE,  os.path.join(SCRIPTS_DIR, "_tmp01.yaml"))
    p02 = m02.apply(p01,   os.path.join(SCRIPTS_DIR, "_tmp02.yaml"))
    p03 = m03.apply(p02,   FINAL)

    # ── Clean up temp files ──────────────────────────────────────────────
    for tmp in ("_tmp01.yaml", "_tmp02.yaml"):
        p = os.path.join(SCRIPTS_DIR, tmp)
        if os.path.exists(p):
            os.remove(p)

    # ── Optional: generate agent config ─────────────────────────────────
    try:
        m04.main()
    except Exception as e:
        print(f"[04] Agent config skipped ({e})")

    # ── Validate ─────────────────────────────────────────────────────────
    print("\n── Validation ──────────────────────────────────────────────")
    v = _validate(FINAL)

    if v["errors"]:
        print("  ❌ ERRORS (fix before deploying):")
        for e in v["errors"]:
            print(f"     {e}")
    else:
        print("  ✅ No errors")

    if v["warnings"]:
        print("  ⚠  WARNINGS:")
        for w in v["warnings"]:
            print(f"     {w}")

    print(f"\n── Final YAML stats ─────────────────────────────────────────")
    print(f"  Output:             {FINAL}")
    print(f"  Verified queries:   {v['vq_count']} ({v['vq_count']-base_vqs:+d} from base)")
    print(f"  Dimensions:         {v['dims']}")
    print(f"  Facts:              {v['facts']}")
    print(f"  Table metrics:      {v['metrics_table']}")
    print(f"  View metrics:       {v['metrics_view']}")
    print(f"  ~Token budget used: {v['tokens']:,} / 32,000")

    print(f"""
── Next steps ───────────────────────────────────────────────
  1.  Review a sample of VQ SQL blocks in:
        {FINAL}

  2.  Run regression audit queries in Snowflake:
        06_regression_test.sql
      Pay attention to TEST 5 (ACCOUNT_LEVEL_3 names) and
      TEST 12 (COST_CENTER_LEVEL_4 names).  Update
      03_enrich_dimensions.py if the names differ from your data.

  3.  Deploy with verify-only first:
        CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
          'ACC_PRD.COST_CENTER',
          $$<paste full YAML>$$,
          TRUE   -- verify_only
        );

  4.  Deploy for real (remove TRUE or pass FALSE).

  5.  Smoke-test in Snowsight Cortex Analyst Playground.

  6.  Build the Streamlit app using:
        05_api_prompt_engineering.py
──────────────────────────────────────────────────────────────
""")

    return 0 if not v["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
