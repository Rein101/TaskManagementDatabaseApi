/* =============================================================================
   OPEX_COST_CENTER_AI  -  deploy a native Snowflake Semantic View
   Target object: ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI
   Source spec:   opex_cost_center_semantic_view.yaml
   =============================================================================

   WHY a native semantic view (not a stage YAML): it validates at CREATE time.
   Bad joins, missing columns, or invalid metric expressions fail HERE instead
   of returning a wrong number to a business user later.

   TWO WAYS TO LOAD THE YAML
   -------------------------
   A) Snowsight (easiest): AI & ML > Cortex Analyst > Semantic Views > Create
      > "Upload YAML file" > pick opex_cost_center_semantic_view.yaml.
   B) Pure SQL: paste the full YAML between the $$ ... $$ markers in step 2/3
      below. (The procedure's 2nd argument is the YAML text itself.)
   ========================================================================== */

-- Use a role that can create the object and read the base tables.
USE ROLE SYSADMIN;            -- or your data-engineering role
USE DATABASE ACC_PRD;
USE SCHEMA  COST_CENTER;
USE WAREHOUSE <YOUR_WH>;

/* ---------------------------------------------------------------------------
   STEP 1 (recommended): VERIFY ONLY.
   Third argument TRUE => parse + validate, create nothing.
   Returns "YAML file is valid..." or throws a precise error (line/column).
--------------------------------------------------------------------------- */
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'ACC_PRD.COST_CENTER',
  $$
-- >>> PASTE THE FULL CONTENTS OF opex_cost_center_semantic_view.yaml HERE <<<
  $$,
  TRUE   -- verify_only
);

/* ---------------------------------------------------------------------------
   STEP 2: CREATE for real (omit the 3rd arg, or pass FALSE).
   Re-running replaces the object's definition.
--------------------------------------------------------------------------- */
CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML(
  'ACC_PRD.COST_CENTER',
  $$
-- >>> PASTE THE FULL CONTENTS OF opex_cost_center_semantic_view.yaml HERE <<<
  $$
);

/* ---------------------------------------------------------------------------
   STEP 3: Confirm it exists and inspect what got created.
--------------------------------------------------------------------------- */
SHOW SEMANTIC VIEWS IN SCHEMA ACC_PRD.COST_CENTER;
DESCRIBE SEMANTIC VIEW ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI;
SHOW SEMANTIC METRICS    IN SEMANTIC VIEW ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI;
SHOW SEMANTIC DIMENSIONS IN SEMANTIC VIEW ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI;

/* ---------------------------------------------------------------------------
   STEP 4: GRANTS
   - The role that ASKS questions through Cortex Analyst needs CORTEX access,
     SELECT on the semantic view, and SELECT on every base table it reads.
   Replace <ANALYST_ROLE> with your consuming role.
--------------------------------------------------------------------------- */
-- Cortex Analyst access (CORTEX_USER covers all Cortex AI features):
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE <ANALYST_ROLE>;

-- Query the semantic view object itself:
GRANT SELECT ON SEMANTIC VIEW ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI TO ROLE <ANALYST_ROLE>;

-- Read the physical tables behind it:
GRANT USAGE ON DATABASE ACC_PRD TO ROLE <ANALYST_ROLE>;
GRANT USAGE ON SCHEMA ACC_PRD.COST_CENTER TO ROLE <ANALYST_ROLE>;
GRANT USAGE ON SCHEMA ACC_PRD.MASTERDATA  TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.COST_CENTER.VW_JEDOX_DATA_OPEX                TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.MASTERDATA.VW_FISCAL_DATE                     TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ACCOUNT       TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_COST_CENTER   TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_ENTITY        TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_FUNC_AREA     TO ROLE <ANALYST_ROLE>;
GRANT SELECT ON ACC_PRD.MASTERDATA.VW_JEDOX_MASTER_DATA_PROFIT_CENTER TO ROLE <ANALYST_ROLE>;

/* ---------------------------------------------------------------------------
   STEP 5: SMOKE TESTS (run as <ANALYST_ROLE>)
--------------------------------------------------------------------------- */
-- 5a. Direct semantic-SQL query (validates metrics + a relationship/join):
SELECT *
FROM SEMANTIC_VIEW(
  ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI
  METRICS    ACTUAL_EUR, BUDGET_EUR, VARIANCE_VS_BUDGET_EUR
  DIMENSIONS VW_JEDOX_MASTER_DATA_ACCOUNT.ACCOUNT_LEVEL_2
)
ORDER BY ACTUAL_EUR DESC
LIMIT 20;

-- 5b. Point Cortex Analyst at it from the Playground:
--     Snowsight > AI & ML > Cortex Analyst > pick OPEX_COST_CENTER_AI, then ask
--     one of the onboarding questions, e.g.:
--     "What are the key drivers of the variance between Actual and Forecast by account?"

-- 5c. Via REST API (the Streamlit app will use this), the request body sets:
--     { "semantic_view": "ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI", "messages": [...] }
--     POST /api/v2/cortex/analyst/message

/* ---------------------------------------------------------------------------
   STEP 6 (CI/CD): round-trip the object back to YAML and commit to Git.
--------------------------------------------------------------------------- */
SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI');
