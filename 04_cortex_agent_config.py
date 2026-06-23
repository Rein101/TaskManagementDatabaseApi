#!/usr/bin/env python3
"""
04_cortex_agent_config.py
──────────────────────────
Generates the full Cortex Agent configuration for the OpEx chatbot.

TWO PATHS — pick one:
  PATH A (recommended, cheapest): Streamlit → Cortex Analyst directly.
          Skip this script; use 05_api_prompt_engineering.py only.
  PATH B (this script): Cortex Agent orchestrates Cortex Analyst as a tool.
          Use when you need multi-tool orchestration (e.g. Analyst + Cortex
          Search over unstructured documents like earnings call transcripts).

The agent adds ~1 Snowpark credit per call on top of the Analyst cost.
Only justify it if you need multi-tool reasoning.

USAGE
  python 04_cortex_agent_config.py
  Prints the system prompt and writes opex_agent_config.json.
"""

import json, textwrap

SEMANTIC_VIEW = "ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI"
AGENT_MODEL   = "mistral-large2"   # cheap orchestration model; Analyst does the heavy lifting

# ═══════════════════════════════════════════════════════════════════════════
# AGENT SYSTEM PROMPT
# This is injected as the system message when calling the Cortex Agent API.
# The agent LLM reads this, decides which tool to call, and formats the reply.
# Keep it concise — every token here costs credits.
# ═══════════════════════════════════════════════════════════════════════════
AGENT_SYSTEM_PROMPT = """\
You are OpEx Insight, an FP&A analytics assistant for the Cybersecurity Data Science team.
Your job is to answer questions about Operating Expense (OpEx) cost-center data using the
opex_analyst tool, and then explain the results clearly in plain business language.

## TOOL USE RULES
1. For ANY question about OpEx costs, variances, FTE counts, trends, or budgets — call opex_analyst first.
2. Do NOT answer data questions from memory. Always call the tool and use its result.
3. If opex_analyst returns an error or says it cannot answer, tell the user clearly and
   suggest rephrasing (more specific period, cost center, or account type).
4. If the user asks something outside the model scope (vendor names, revenue, AR, install base),
   explain what IS available and offer the nearest alternative query.

## RESPONSE FORMAT
After the tool returns results:
1. Write a HEADLINE: one sentence with the top-level number and direction.
2. Write KEY DRIVERS (max 4 bullet points): biggest contributors to the variance or trend.
   Include the account type, cost center, EUR amount, and % change.
3. Write NOTABLE ITEMS: flag anything >5% variance or >€50K absolute that is not in key drivers.
4. Write OFFSETS (if applicable): items that moved favorably and partially offset unfavorables.
5. Suggest 1-2 FOLLOW-UP QUESTIONS the user might want to ask next.

## STYLE RULES
- Lead with numbers: "Q1 OpEx came in at €4.2M vs forecast €3.9M (+€0.3M, +7.7%)".
- Use K for thousands, M for millions: "€320K unfavorable".
- Positive variance = over forecast/budget (unfavorable for cost).
- Negative variance = under forecast/budget (favorable for cost).
- Never say "I don't have access to" — just say what the model covers and what it doesn't.
- Keep commentary under 200 words unless the user asks for a detailed explanation.

## SCOPE GUARDRAILS
This model covers: OPEX and headcount/FTE by account, cost center, profit center, entity,
functional area, and period. It does NOT contain vendor detail, AR, revenue, or install base.
Fiscal year starts October. Default: current fiscal year. ACT vs FCST uses latest forecast.
"""

# ═══════════════════════════════════════════════════════════════════════════
# TOOL DEFINITION for Cortex Agent API
# POST /api/v2/cortex/agent:run
# ═══════════════════════════════════════════════════════════════════════════
TOOL_DEFINITION = {
    "tool_spec": {
        "type":   "cortex_analyst_text_to_sql",
        "name":   "opex_analyst",
        "spec": {
            "semantic_view": SEMANTIC_VIEW
        }
    }
}

TOOL_RESOURCES = {
    "opex_analyst": {
        "semantic_view": SEMANTIC_VIEW
    }
}


def build_agent_request(user_question: str, history: list[dict] | None = None) -> dict:
    """
    Build the complete Cortex Agent API request body.

    Args:
        user_question: The user's natural-language question.
        history:       List of prior {role, content} messages for multi-turn support.

    Returns:
        Dict ready to serialize as JSON for POST /api/v2/cortex/agent:run
    """
    messages = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_question})

    return {
        "model":          AGENT_MODEL,
        "messages":       messages,
        "tools":          [TOOL_DEFINITION],
        "tool_resources": TOOL_RESOURCES,
        "response_instruction": (
            "Always respond in the format: HEADLINE | KEY DRIVERS | NOTABLE ITEMS | FOLLOW-UP QUESTIONS. "
            "Use EUR with K/M suffixes. Positive variance = unfavorable."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# SNOWFLAKE SQL — OPTIONAL: create a named Cortex Agent stored procedure
# that wraps the REST call so it can be called from Snowflake tasks or
# Streamlit without managing bearer tokens manually.
# ═══════════════════════════════════════════════════════════════════════════
AGENT_WRAPPER_SQL = f"""\
-- Create a Snowflake stored procedure that calls the Cortex Agent API.
-- The procedure returns the agent's text response for a given question.
-- Grant EXECUTE on this procedure to your Streamlit role.

CREATE OR REPLACE PROCEDURE ACC_PRD.COST_CENTER.OPEX_AGENT_ASK(question VARCHAR)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
AS
$$
import _snowflake, json

def run(session, question):
    request_body = {{
        "model": "{AGENT_MODEL}",
        "messages": [
            {{"role": "system", "content": {json.dumps(AGENT_SYSTEM_PROMPT)}}},
            {{"role": "user",   "content": question}}
        ],
        "tools": [{{
            "tool_spec": {{
                "type": "cortex_analyst_text_to_sql",
                "name": "opex_analyst",
                "spec": {{"semantic_view": "{SEMANTIC_VIEW}"}}
            }}
        }}],
        "tool_resources": {{
            "opex_analyst": {{"semantic_view": "{SEMANTIC_VIEW}"}}
        }}
    }}
    response = _snowflake.send_snow_api_request(
        "POST", "/api/v2/cortex/agent:run",
        {{}}, {{}}, request_body, {{}}, 60000
    )
    if response.get("status") != 200:
        return {{"error": response}}
    return response.get("content", {{}})
$$;

GRANT EXECUTE ON PROCEDURE ACC_PRD.COST_CENTER.OPEX_AGENT_ASK(VARCHAR) TO ROLE <ANALYST_ROLE>;
"""


def main():
    example = build_agent_request(
        "What are the key drivers of the ACT vs FCST variance this fiscal year by account?"
    )
    out_path = "opex_agent_config.json"
    with open(out_path, "w") as fh:
        json.dump({
            "system_prompt":    AGENT_SYSTEM_PROMPT,
            "tool_definition":  TOOL_DEFINITION,
            "tool_resources":   TOOL_RESOURCES,
            "example_request":  example,
        }, fh, indent=2)

    print(f"[04] Cortex Agent config → {out_path}")
    print(f"     model:          {AGENT_MODEL}")
    print(f"     semantic_view:  {SEMANTIC_VIEW}")
    print()
    print("─── AGENT SQL WRAPPER (create in Snowflake if using PATH B) ────────")
    print(AGENT_WRAPPER_SQL[:400], "…")
    print()
    print("─── SYSTEM PROMPT PREVIEW ──────────────────────────────────────────")
    print(textwrap.shorten(AGENT_SYSTEM_PROMPT, width=200))

    # Also write the SQL
    with open("opex_agent_wrapper.sql", "w") as fh:
        fh.write(AGENT_WRAPPER_SQL)
    print(f"\n[04] Agent SQL wrapper → opex_agent_wrapper.sql")


if __name__ == "__main__":
    main()
