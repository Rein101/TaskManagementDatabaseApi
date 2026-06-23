#!/usr/bin/env python3
"""
05_api_prompt_engineering.py
─────────────────────────────
A plug-and-play library for the Streamlit app.  Import this file directly.
Handles everything between the user typing a question and a polished response
appearing on screen — the Cortex Analyst API call, result enrichment, and
AI-generated commentary.

ARCHITECTURE (PATH A — direct, no Cortex Agent)
  User question
      │
      ▼
  pre_process_question()      ← injects fiscal context, resolves shortcuts
      │
      ▼
  analyst_request()           ← POST /api/v2/cortex/analyst/message
      │
      ▼
  parse_analyst_response()    ← extracts SQL + table + error
      │
      ▼
  commentary_prompt()         ← builds the AI_COMPLETE / AI commentary call
      │
      ▼
  format_commentary()         ← structures the FP&A narrative

USAGE IN STREAMLIT
  import sys; sys.path.append("/path/to/scripts")
  from 05_api_prompt_engineering import *

  body   = analyst_request(user_question, conversation_history)
  result = call_analyst_api(body)      # wrapper for _snowflake.send_snow_api_request
  parsed = parse_analyst_response(result)
  if parsed["type"] == "sql":
      df   = session.sql(parsed["sql"]).to_pandas()
      cmmt = commentary_prompt(user_question, parsed["sql"], df)
      narrative = session.sql(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2', $${cmmt}$$)").collect()[0][0]
"""

import json, re
from datetime import date
from calendar import month_name

# ───────────────────────────────────────────────────────────────────────────
SEMANTIC_VIEW    = "ACC_PRD.COST_CENTER.OPEX_COST_CENTER_AI"
ANALYST_ENDPOINT = "/api/v2/cortex/analyst/message"
COMMENTARY_MODEL = "mistral-large2"   # cheap, fast; change to claude-3-5-sonnet for richer prose

# ───────────────────────────────────────────────────────────────────────────
# FISCAL CONTEXT HELPERS
# ───────────────────────────────────────────────────────────────────────────
def _current_fy_label() -> str:
    today = date.today()
    fy = today.year + 1 if today.month >= 10 else today.year
    return f"FY{str(fy)[2:]}"          # e.g. "FY26"


def _current_quarter() -> str:
    month = date.today().month
    if   month in (10, 11, 12): return "Q1"
    elif month in (1, 2, 3):    return "Q2"
    elif month in (4, 5, 6):    return "Q3"
    else:                        return "Q4"


def _fy_range_text() -> str:
    today = date.today()
    if today.month >= 10:
        return f"Oct {today.year} – Sep {today.year + 1}"
    return f"Oct {today.year - 1} – Sep {today.year}"


SHORTHAND_MAP = {
    "ytd":             f"year-to-date for {_current_fy_label()} (October through the latest closed month)",
    "this fy":         f"fiscal year {_current_fy_label()} ({_fy_range_text()})",
    "current fy":      f"fiscal year {_current_fy_label()} ({_fy_range_text()})",
    "this quarter":    f"fiscal {_current_quarter()} of {_current_fy_label()}",
    "q1":              f"Q1 of {_current_fy_label()} (Oct–Dec)",
    "q2":              f"Q2 of {_current_fy_label()} (Jan–Mar)",
    "q3":              f"Q3 of {_current_fy_label()} (Apr–Jun)",
    "q4":              f"Q4 of {_current_fy_label()} (Jul–Sep)",
    "act vs fcst":     "Actual vs latest Forecast version",
    "act vs forecast": "Actual vs latest Forecast version",
    "act vs budget":   "Actual vs Budget X",
}


# ═══════════════════════════════════════════════════════════════════════════
# 1. PRE-PROCESSOR — enrich user question before sending to Cortex Analyst
# ═══════════════════════════════════════════════════════════════════════════
def pre_process_question(raw: str) -> str:
    """
    Expand fiscal shorthand so Cortex Analyst always has an unambiguous period
    and version.  Lightweight: only appends a context suffix, never rephrases.

    Args:
        raw: the user's raw question string

    Returns:
        Enriched question string (or the original if no expansion needed)
    """
    lower = raw.lower()
    expansions = []
    for shorthand, expansion in SHORTHAND_MAP.items():
        if shorthand in lower:
            expansions.append(expansion)

    # Always append the current-FY anchor so the model knows today's date context
    today_str = date.today().strftime("%B %Y")
    context = f"[Context: today is {today_str}; current fiscal year is {_current_fy_label()} ({_fy_range_text()}).]"

    if expansions:
        clarification = "; ".join(set(expansions))
        return f"{raw.strip()}  [{clarification}]  {context}"
    return f"{raw.strip()}  {context}"


# ═══════════════════════════════════════════════════════════════════════════
# 2. ANALYST REQUEST BUILDER — constructs the Cortex Analyst API body
# ═══════════════════════════════════════════════════════════════════════════
def analyst_request(question: str, history: list[dict] | None = None) -> dict:
    """
    Build the POST body for /api/v2/cortex/analyst/message.

    Args:
        question: pre-processed user question
        history:  list of prior {role, content} turns for multi-turn sessions

    Returns:
        dict ready for JSON serialization
    """
    enriched = pre_process_question(question)
    messages = []
    if history:
        # Replay prior turns so the model has full conversation context
        for turn in history:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": enriched})

    return {
        "semantic_view": SEMANTIC_VIEW,
        "messages":      messages,
    }


def call_analyst_api(body: dict, snowflake_module=None, timeout_ms: int = 50_000) -> dict:
    """
    Call the Cortex Analyst REST API from within Streamlit-in-Snowflake.

    Args:
        body:             request body from analyst_request()
        snowflake_module: pass the `_snowflake` module object imported in Streamlit.
                          If None, returns a mock structure for local testing.
        timeout_ms:       API timeout in milliseconds

    Returns:
        Parsed JSON response dict
    """
    if snowflake_module is None:
        # Local test stub — returns a minimal shape
        return {"status": 200, "content": {"type": "text", "text": "[TEST MODE — no Snowflake connection]"}}

    resp = snowflake_module.send_snow_api_request(
        "POST", ANALYST_ENDPOINT,
        {}, {},                     # headers, params (leave empty)
        body,
        {},                         # extra options
        timeout_ms,
    )
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# 3. RESPONSE PARSER
# ═══════════════════════════════════════════════════════════════════════════
def parse_analyst_response(response: dict) -> dict:
    """
    Extract the useful parts from a Cortex Analyst API response.

    Returns a dict with keys:
        type        : "sql" | "text" | "suggestions" | "error"
        sql         : the SQL string (if type=="sql")
        text        : narrative text from the model (if type=="text")
        suggestions : list of suggested follow-up questions
        request_id  : for feedback submission
        raw         : full raw response
    """
    out = {"type": "error", "sql": None, "text": None, "suggestions": [], "request_id": None, "raw": response}

    if response.get("status", 0) != 200:
        out["text"] = f"API error {response.get('status')}: {response}"
        return out

    content = response.get("content") or {}
    # Cortex Analyst returns a list of content blocks
    if isinstance(content, list):
        blocks = content
    elif isinstance(content, dict):
        blocks = content.get("message", {}).get("content", [])
    else:
        blocks = []

    out["request_id"] = (content.get("request_id") if isinstance(content, dict) else None)

    for block in blocks:
        btype = block.get("type")
        if btype == "sql":
            out["type"] = "sql"
            out["sql"]  = block.get("statement") or block.get("sql") or ""
        elif btype == "text":
            out["text"] = block.get("text", "")
            if out["type"] == "error":
                out["type"] = "text"
        elif btype == "suggestions":
            out["suggestions"] = block.get("suggestions", [])

    return out


# ═══════════════════════════════════════════════════════════════════════════
# 4. COMMENTARY PROMPT — the FP&A narrative generation prompt
# ═══════════════════════════════════════════════════════════════════════════
def commentary_prompt(
    user_question: str,
    sql: str,
    result_rows: list[dict],
    max_rows_in_prompt: int = 30,
) -> str:
    """
    Build the prompt for the commentary AI_COMPLETE call.
    Pass the output to SNOWFLAKE.CORTEX.COMPLETE(model, prompt).

    Args:
        user_question:     the original question the user asked
        sql:               the SQL Cortex Analyst generated
        result_rows:       the query results as a list of dicts (e.g. df.to_dict('records'))
        max_rows_in_prompt: cap how much result data goes into the prompt

    Returns:
        String prompt for the commentary LLM
    """
    # Truncate for token budget — take the rows with the largest absolute values
    sample = result_rows[:max_rows_in_prompt]
    result_json = json.dumps(sample, default=str, indent=None)

    return f"""\
You are an FP&A analyst writing the variance commentary section of a U+4 financial review.
The data below was retrieved from the OpEx cost-center analytics model.

USER QUESTION: {user_question}

SQL GENERATED:
{sql}

RESULT DATA (up to {max_rows_in_prompt} rows):
{result_json}

INSTRUCTIONS:
Write concise FP&A commentary following this EXACT structure:

HEADLINE
One sentence. Lead with the top-level EUR figure, comparison benchmark, and direction.
Example: "Q1 FY26 OpEx came in at €4.2M vs forecast €3.9M (+€0.3M, +7.7% unfavorable)."

KEY DRIVERS
Up to 4 bullet points. Each must include: account/cost-center, EUR amount, % change, brief reason (if inferable from the data).
Example: "• Consulting (AMS): +€180K (+22%) — contract ramp-up in Jan"

OFFSETS
Up to 2 bullet points of favorable items (negative variance) that partially offset the unfavorables.
Omit this section if everything moved in the same direction.

NOTABLE ITEMS
Flag any row where: absolute variance > €50K OR variance % > 10%.
Keep to 1–2 sentences.

FOLLOW-UP QUESTIONS
Suggest 2 natural follow-up questions the user might want to ask next.
These must be answerable from the OpEx model (cost, FTE, trend, account drill, entity).

STYLE RULES
- Positive variance = over forecast/budget = unfavorable (flag clearly).
- Negative variance = under forecast/budget = favorable.
- Use K for thousands, M for millions: €320K, €1.4M.
- Round to 1 decimal for percentages, 0 decimals for K/M.
- Total commentary (excluding follow-up questions) must be under 200 words.
- Do NOT invent numbers that are not in the data.
- Do NOT speculate about root causes beyond what the data shows.
"""


# ═══════════════════════════════════════════════════════════════════════════
# 5. FEEDBACK HELPER — submit thumbs-up / thumbs-down to Cortex
# ═══════════════════════════════════════════════════════════════════════════
FEEDBACK_ENDPOINT = "/api/v2/cortex/analyst/feedback"

def submit_feedback(request_id: str, positive: bool, snowflake_module=None) -> bool:
    """
    Submit feedback for a Cortex Analyst response.
    Returns True if the API accepted it.
    """
    if snowflake_module is None or not request_id:
        return False
    body = {"request_id": request_id, "positive": positive}
    resp = snowflake_module.send_snow_api_request(
        "POST", FEEDBACK_ENDPOINT, {}, {}, body, {}, 10_000
    )
    return resp.get("status") == 200


# ═══════════════════════════════════════════════════════════════════════════
# 6. QUESTION TEMPLATE LIBRARY — pre-built starters for the Streamlit UI
#    These populate a "Suggested questions" sidebar / button bar.
# ═══════════════════════════════════════════════════════════════════════════
QUESTION_TEMPLATES = {
    "ACT vs FCST": [
        "What are the key drivers of the ACT vs FCST variance by account this fiscal year?",
        "Show ACT vs FCST variance by cost center for the current fiscal year.",
        "Which cost centers are over forecast by more than 10% this fiscal year?",
        "What are the top 5 accounts by absolute ACT vs FCST variance?",
    ],
    "ACT vs Budget": [
        "Show Actual vs Budget variance by profit center YTD.",
        "What is the budget utilization rate by cost center?",
        "Compare full-year forecast to annual budget by account category.",
        "Show the ACT vs Budget variance for the current fiscal year by account hierarchy.",
    ],
    "Trends": [
        "Show the monthly OPEX trend comparing this fiscal year to last year.",
        "Show the 18-month compensation spend trend by cost center.",
        "What is the month-over-month OPEX change for the last 6 months?",
        "Show the OPEX by fiscal quarter for the current year — Q1 through Q4 progression.",
    ],
    "Headcount / FTE": [
        "Show FTE headcount by entity and region for the current fiscal year.",
        "What is the OpEx cost per FTE by cost center?",
        "Show the net FTE month-over-month change over the last 12 months.",
        "What is the FTE count trend over the last 18 months?",
    ],
    "Cost Breakdown": [
        "Break down spend by cost type (consulting, tech cost, contractor) this fiscal year.",
        "What percentage of total OPEX is employee compensation by cost center?",
        "Show controllable (non-compensation) OPEX by cost center.",
        "Show total OPEX by account category in thousands and millions.",
    ],
    "YoY Comparison": [
        "Compare this fiscal year vs last fiscal year by cost center — where did spending change most?",
        "Compare this fiscal year vs last fiscal year by account — where are the biggest changes?",
        "Which accounts show year-over-year cost reductions? Identify efficiency gains.",
        "Compare Q2 this fiscal year vs Q2 last fiscal year by account hierarchy.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# 7. SNOWFLAKE CALL WRAPPER (for direct use in Streamlit scripts)
# ═══════════════════════════════════════════════════════════════════════════
STREAMLIT_SNIPPET = """\
# ─── Paste this block into your Streamlit app ───────────────────────────────
import _snowflake, json
from snowflake.snowpark.context import get_active_session
# import sys; sys.path.append("/path/to/scripts")
from prompts_05 import analyst_request, call_analyst_api, parse_analyst_response
from prompts_05 import commentary_prompt, submit_feedback, QUESTION_TEMPLATES

session = get_active_session()

def ask_opex(question: str, history=None):
    body   = analyst_request(question, history)
    result = call_analyst_api(body, _snowflake)
    parsed = parse_analyst_response(result)

    if parsed["type"] == "sql" and parsed["sql"]:
        df = session.sql(parsed["sql"]).to_pandas()
        cmmt_prompt = commentary_prompt(question, parsed["sql"], df.head(30).to_dict("records"))
        narrative = session.sql(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE(?, ?)",
            params=["mistral-large2", cmmt_prompt]
        ).collect()[0][0]
        return {"df": df, "sql": parsed["sql"], "commentary": narrative,
                "suggestions": parsed["suggestions"], "request_id": parsed["request_id"]}

    return {"df": None, "sql": None, "commentary": parsed.get("text", "No result."),
            "suggestions": parsed["suggestions"], "request_id": parsed["request_id"]}
# ────────────────────────────────────────────────────────────────────────────
"""


def main():
    """Quick self-test / demo of pre-processing and template list."""
    test_questions = [
        "What drove costs up ytd?",
        "Show ACT vs FCST by cost center this fy",
        "Break down q2 spending by account",
    ]
    print("=== PRE-PROCESSOR DEMO ===")
    for q in test_questions:
        print(f"IN:  {q}")
        print(f"OUT: {pre_process_question(q)}")
        print()

    print("=== QUESTION TEMPLATES ===")
    for category, qs in QUESTION_TEMPLATES.items():
        print(f"\n{category}")
        for q in qs:
            print(f"  • {q}")

    print("\n=== STREAMLIT SNIPPET ===")
    print(STREAMLIT_SNIPPET)


if __name__ == "__main__":
    main()
