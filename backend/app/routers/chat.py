from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import math
import re

from app.database import get_db
from app.models import Company, FinancialMetric
from app.schemas import ChatRequest, ChatResponse, ChartData, ChartSeries
from app.llm import call_llm

router = APIRouter()


def get_last_n_years_metrics(
    db: Session, company_id: int, metric_names: List[str], n: int = 3
):
    """
    Returns (years, {metric_name: {year: value}})
    """
    q = (
        db.query(FinancialMetric)
        .filter(
            FinancialMetric.company_id == company_id,
            FinancialMetric.metric_name.in_(metric_names),
        )
        .order_by(FinancialMetric.year.desc())
    )
    rows = q.all()
    result = {m: {} for m in metric_names}
    years = set()
    for row in rows:
        if len(result[row.metric_name]) >= n:
            continue
        result[row.metric_name][row.year] = row.value
        years.add(row.year)
    years = sorted(list(years))
    return years, result
def _normalize(text: str) -> str:
    # keep letters and spaces, lowercase
    return "".join(ch for ch in text.lower() if ch.isalpha() or ch.isspace()).strip()

def _is_greeting(text: str) -> bool:
    normalized = _normalize(text)
    greeting_keywords = [
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    ]
    return any(
        normalized == kw or normalized.startswith(kw + " ")
        for kw in greeting_keywords
    ) and len(normalized.split()) <= 5

def _is_smalltalk_or_overview(text: str) -> bool:
    """
    Detect vague/overview/smalltalk questions where we want a quick summary,
    not a full LLM analysis.
    """
    normalized = _normalize(text)
    # phrases that usually mean "give me a quick overview"
    overview_phrases = [
        "overview", "high level", "highlevel", "summary", "quick summary",
        "tell me something", "tell me about", "anything interesting",
        "how are we doing", "how is business", "how’s business", "hows business",
        "what do you know", "where do we stand", "status", "performance summary",
        "company summary", "quick recap", "recap",
    ]
    # short/very generic small talk
    smalltalk_phrases = [
        "what's up", "whats up", "sup", "yo",
        "how are you", "how are u", "how r u",
    ]
    # quick heuristic: either it contains one of these phrases, or it's very short and generic
    if any(phrase in normalized for phrase in overview_phrases + smalltalk_phrases):
        return True
    # also treat very short generic asks like "tell me more" as overview
    if len(normalized.split()) <= 4 and any(w in normalized for w in ["summary", "overview", "status", "update"]):
        return True
    return False

def _fmt_pct(x: float) -> str:
    return f"{x:.1f}%"

def _safe_ratio(n: float, d: float) -> float | None:
    try:
        if d and d != 0:
            return n / d
    except Exception:
        pass
    return None

def _build_quick_overview(company_name: str, years: list[int], metrics: dict, role: str) -> str:
    """
    Make a tight, role-aware summary using whatever we have (revenue & net_profit).
    Avoids any LLM call for speed.
    """
    if not years:
        return (
            f"{company_name}: I don’t have financial data yet. "
            "Upload a balance sheet PDF or seed metrics to get a quick summary."
        )

    years_sorted = sorted(years)
    # Pull series (may have gaps)
    rev_series = [metrics.get("revenue", {}).get(y) for y in years_sorted]
    pat_series = [metrics.get("net_profit", {}).get(y) for y in years_sorted]

    # Compute basics
    first_rev = next((v for v in rev_series if v is not None), None)
    last_rev = next((rev_series[-i] for i in range(1, len(rev_series) + 1) if rev_series[-i] is not None), None)

    first_pat = next((v for v in pat_series if v is not None), None)
    last_pat = next((pat_series[-i] for i in range(1, len(pat_series) + 1) if pat_series[-i] is not None), None)

    # YoY (last vs prev)
    yoy_rev = None
    yoy_pat = None
    if len(years_sorted) >= 2:
        prev_rev = rev_series[-2]
        if last_rev is not None and prev_rev not in (None, 0):
            yoy_rev = (last_rev / prev_rev - 1) * 100.0
        prev_pat = pat_series[-2]
        if last_pat is not None and prev_pat not in (None, 0):
            yoy_pat = (last_pat / prev_pat - 1) * 100.0

    # CAGR across available points
    cagr_rev = None
    if first_rev not in (None, 0) and last_rev not in (None,) and len(years_sorted) >= 2:
        periods = len(years_sorted) - 1
        try:
            cagr_rev = (last_rev / first_rev) ** (1 / periods) - 1
            cagr_rev *= 100.0
        except Exception:
            cagr_rev = None

    # Margin for last year
    margin_last = None
    if last_rev not in (None, 0) and last_pat is not None:
        r = _safe_ratio(last_pat, last_rev)
        if r is not None:
            margin_last = r * 100.0

    yr_str = f"FY {years_sorted[0]}–{years_sorted[-1]}" if len(years_sorted) > 1 else f"FY {years_sorted[0]}"

    # Craft role-aware copy
    lines = []
    if "ceo" in role.lower():
        lines.append(f"{company_name} — {yr_str} overview:")
        if last_rev is not None:
            s = f"Revenue ended at {last_rev:,.0f}"
            if yoy_rev is not None:
                s += f" ({_fmt_pct(yoy_rev)} YoY)"
            if cagr_rev is not None:
                s += f", {_fmt_pct(cagr_rev)} CAGR"
            lines.append("• " + s + ".")
        if last_pat is not None:
            s = f"Net profit at {last_pat:,.0f}"
            if yoy_pat is not None:
                s += f" ({_fmt_pct(yoy_pat)} YoY)"
            if margin_last is not None:
                s += f", margin {_fmt_pct(margin_last)}"
            lines.append("• " + s + ".")
        lines.append("• Ask for specifics like: revenue by year, margins, or key ratios.")
    elif "analyst" in role.lower():
        lines.append(f"{company_name} — quick performance summary ({yr_str}):")
        if last_rev is not None:
            s = f"Revenue {years_sorted[-1]}: {last_rev:,.0f}"
            if yoy_rev is not None:
                s += f" ({_fmt_pct(yoy_rev)} YoY)"
            if cagr_rev is not None:
                s += f", CAGR {_fmt_pct(cagr_rev)}"
            lines.append("• " + s + ".")
        if last_pat is not None:
            s = f"PAT {years_sorted[-1]}: {last_pat:,.0f}"
            if yoy_pat is not None:
                s += f" ({_fmt_pct(yoy_pat)} YoY)"
            if margin_last is not None:
                s += f", margin {_fmt_pct(margin_last)}"
            lines.append("• " + s + ".")
        lines.append("• Tip: ask for trends, ratios (e.g., debt-to-equity), or segment performance.")
    else:
        lines.append(f"{company_name}: executive snapshot ({yr_str}).")
        bits = []
        if last_rev is not None:
            core = f"Revenue {last_rev:,.0f}"
            if yoy_rev is not None:
                core += f" ({_fmt_pct(yoy_rev)} YoY)"
            bits.append(core)
        if last_pat is not None:
            core = f"PAT {last_pat:,.0f}"
            if margin_last is not None:
                core += f", margin {_fmt_pct(margin_last)}"
            bits.append(core)
        if bits:
            lines.append("• " + " | ".join(bits) + ".")
        lines.append("• You can ask: “trend of revenue and profit”, “assets vs liabilities”, or “key risks”.")
    return "\n".join(lines)


@router.post("/query", response_model=ChatResponse)
def chat_query(payload: ChatRequest, db: Session = Depends(get_db)):
    # 1. Company lookup
    company = db.query(Company).filter(Company.code == payload.company_code).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 2. Demo: use revenue + net_profit for last 3 years
    metric_names = ["revenue", "net_profit"]
    years, metrics = get_last_n_years_metrics(db, company.id, metric_names, n=3)

    # 3. Build data context string
    if years:
        data_lines = []
        for y in years:
            rev = metrics["revenue"].get(y)
            pat = metrics["net_profit"].get(y)
            data_lines.append(f"FY {y}: revenue={rev}, net_profit={pat}")
        data_context = "\n".join(data_lines)
    else:
        data_context = "No financial data available."

        # 4. Get the user's latest message
    user_question = payload.messages[-1].content if payload.messages else ""

    # ---- NEW: greetings ----
    if _is_greeting(user_question):
        greeting_answer = (
            f"Hi! I'm your financial copilot for {company.name}. "
            "You can ask me about revenue, profit, assets, liabilities, trends, "
            "or ratios based on the company's published balance sheet."
        )
        return ChatResponse(answer=greeting_answer, chart_data=None)

    # ---- NEW: vague/overview -> quick summary without LLM ----
    if _is_smalltalk_or_overview(user_question):
        overview = _build_quick_overview(company.name, years, metrics, payload.role)
        # Optional: include simple chart_data for context
        chart_data = None
        if years:
            series = []
            if metrics["revenue"]:
                series.append(
                    ChartSeries(
                        label="Revenue",
                        values=[metrics["revenue"].get(y, 0.0) for y in years],
                    )
                )
            if metrics["net_profit"]:
                series.append(
                    ChartSeries(
                        label="Net Profit",
                        values=[metrics["net_profit"].get(y, 0.0) for y in years],
                    )
                )
            chart_data = ChartData(years=years, series=series)
        return ChatResponse(answer=overview, chart_data=chart_data)
# 4. System prompt tuned by role
    system_prompt = (
        "You are a financial analyst assistant for balance sheet and P&L analysis. "
        "You MUST base your answer ONLY on the data provided in the context. "
        "If a specific number or year is not provided, say you don't have that information."
    )

    rl = payload.role.lower()
    if "ceo" in rl:
        system_prompt += (
            " The user is a CEO. Be concise, focus on key trends, risks, and actions, "
            "not too much raw detail."
        )
    elif "analyst" in rl:
        system_prompt += (
            " The user is an analyst. Be detailed, mention actual figures and explain the trends."
        )
    else:
        system_prompt += (
            " The user is senior management. Provide an executive summary with some key numbers."
        )

    # 5. Compose final user prompt for Gemini
    full_user_prompt = f"""
Company: {company.name}
Role: {payload.role}

Available financial data (up to last 3 years):
{data_context}

User question:
{user_question}

Using ONLY the data above, answer the question. Do not invent years or numbers you do not see.
"""

    llm_answer = call_llm(system_prompt, full_user_prompt)

    # 6. Build chart_data for frontend (simple for now)
    chart_data = None
    if years:
        series = []
        if metrics["revenue"]:
            series.append(
                ChartSeries(
                    label="Revenue",
                    values=[metrics["revenue"].get(y, 0.0) for y in years],
                )
            )
        if metrics["net_profit"]:
            series.append(
                ChartSeries(
                    label="Net Profit",
                    values=[metrics["net_profit"].get(y, 0.0) for y in years],
                )
            )
        chart_data = ChartData(years=years, series=series)

    return ChatResponse(answer=llm_answer, chart_data=chart_data)
