from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Tuple, Dict
import math
import re

from app.database import get_db
from app.models import Company, FinancialMetric, Document
from app.schemas import ChatRequest, ChatResponse, ChartData, ChartSeries
from app.llm import call_llm
from app.retrieval import retrieve_relevant_chunks
from app.charts import plan_chart_config, build_chart_data_from_plan

router = APIRouter()


def get_last_n_years_metrics(
    db: Session, company_id: int, metric_names: List[str], n: int = 3
) -> Tuple[List[int], Dict[str, Dict[int, float]]]:
    """
    Returns (years, {metric_name: {year: value}}) for company-based metrics
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


def get_metrics_for_document(
    db: Session, document_id: int, metric_names: List[str], n: int = 10
) -> Tuple[List[int], Dict[str, Dict[int, float]]]:
    """
    Returns (years, {metric_name: {year: value}}) for document-based metrics.
    Gets all available metrics (up to n years) from the uploaded document.
    """
    q = (
        db.query(FinancialMetric)
        .filter(
            FinancialMetric.document_id == document_id,
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
    # Determine context: document_id (preferred) or company_code (legacy)
    company_name = None
    fiscal_year = None
    years = []
    metrics = {}
    
    if payload.document_id:
        # Document-based context (uploaded PDF)
        doc = db.query(Document).filter(Document.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        company_name = doc.company_name or "Unknown Company"
        fiscal_year = doc.fiscal_year
        
        # Get all available metrics from the document
        metric_names = ["revenue", "net_profit", "total_assets", "total_liabilities"]
        years, metrics = get_metrics_for_document(db, doc.id, metric_names, n=10)
    
    elif payload.company_code:
        # Legacy company-based context (seeded data)
        company = db.query(Company).filter(Company.code == payload.company_code).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        company_name = company.name
        metric_names = ["revenue", "net_profit"]
        years, metrics = get_last_n_years_metrics(db, company.id, metric_names, n=3)
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either document_id or company_code must be provided"
        )
    
    # Build data context string with all available metrics
    if years:
        data_lines = []
        for y in sorted(years):
            parts = [f"FY {y}:"]
            if "revenue" in metrics and metrics["revenue"].get(y) is not None:
                parts.append(f"revenue={metrics['revenue'].get(y)}")
            if "net_profit" in metrics and metrics["net_profit"].get(y) is not None:
                parts.append(f"net_profit={metrics['net_profit'].get(y)}")
            if "total_assets" in metrics and metrics["total_assets"].get(y) is not None:
                parts.append(f"total_assets={metrics['total_assets'].get(y)}")
            if "total_liabilities" in metrics and metrics["total_liabilities"].get(y) is not None:
                parts.append(f"total_liabilities={metrics['total_liabilities'].get(y)}")
            if len(parts) > 1:  # Only add if we have at least one metric
                data_lines.append(" ".join(parts))
        data_context = "\n".join(data_lines) if data_lines else "No financial data available."
    else:
        data_context = "No financial data available."
    
    # Get the user's latest message
    user_question = payload.messages[-1].content if payload.messages else ""
    
    # ---- Detect visualization intent ----
    q_lower = user_question.lower()
    wants_visualization = any(
        kw in q_lower
        for kw in ["show", "visualize", "visualise", "plot", "graph", "chart", "draw", "diagram"]
    )
    
    # ---- Build metrics_by_year dict for chart planner ----
    metrics_by_year: Dict[int, Dict[str, float]] = {}
    if years:
        for y in years:
            metrics_by_year[y] = {}
            for metric_name in ["revenue", "net_profit", "total_assets", "total_liabilities"]:
                if metric_name in metrics and metrics[metric_name].get(y) is not None:
                    metrics_by_year[y][metric_name] = metrics[metric_name][y]
    
    # ---- Greetings ----
    if _is_greeting(user_question):
        greeting_answer = (
            f"Hi! I'm your financial copilot for {company_name}. "
            "You can ask me about revenue, profit, assets, liabilities, trends, "
            "or ratios based on the uploaded balance sheet document."
        )
        if fiscal_year:
            greeting_answer += f" This document covers {fiscal_year}."
        return ChatResponse(answer=greeting_answer, chart_data=None)
    
    # ---- Vague/overview -> quick summary without LLM ----
    if _is_smalltalk_or_overview(user_question):
        overview = _build_quick_overview(company_name, years, metrics, payload.role)
        # Only show chart if user explicitly asked for visualization
        chart_data = None
        if wants_visualization and metrics_by_year:
            plan = plan_chart_config(user_question, metrics_by_year)
            if plan.get("wants_chart"):
                chart_data_dict = build_chart_data_from_plan(plan, metrics_by_year)
                if chart_data_dict:
                    # Convert dict to ChartData model
                    from app.schemas import ChartData, ChartSeries
                    chart_data = ChartData(
                        chart_type=chart_data_dict["chart_type"],
                        years=chart_data_dict["years"],
                        series=[ChartSeries(**s) for s in chart_data_dict["series"]]
                    )
        return ChatResponse(answer=overview, chart_data=chart_data)
    
    # ---- RAG: Retrieve relevant text chunks (only for document-based queries) ----
    rag_chunks = []
    text_context = ""
    if payload.document_id:
        try:
            rag_chunks = retrieve_relevant_chunks(
                db=db,
                document_id=payload.document_id,
                question=user_question,
                top_k=12,  # Increased from 5 to get better coverage, especially for MD&A questions
            )
            if rag_chunks:
                joined = "\n\n---\n\n".join(rag_chunks)
                # Increased limit to allow more context for complex questions
                text_context = joined[:6000] if len(joined) > 6000 else joined
        except Exception as e:
            # Log but continue - RAG is optional, metrics still work
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("RAG retrieval failed for document %s: %s", payload.document_id, e)
    
    # ---- System prompt tuned by role ----
    system_prompt = (
        "You are a financial analyst assistant. You answer questions about a company's performance "
        "STRICTLY based on the following:\n\n"
        "1. Structured financial metrics provided to you (revenues, net profits, assets, liabilities, by year).\n"
        "2. Text excerpts taken directly from the company's official balance sheet / annual report PDF.\n\n"
        "Important context about annual reports:\n"
        "* Annual reports typically contain multiple sections: Management Discussion and Analysis (MD&A), "
        "Financial Statements, Notes to Accounts, and Auditor's Reports.\n"
        "* Management Discussion and Analysis (MD&A) sections contain explanations, reasons, strategies, "
        "risks, and management's perspective on performance changes.\n"
        "* Financial Statements contain the actual numbers (revenues, profits, assets, etc.).\n"
        "* Auditor's Reports contain audit opinions and procedures, but NOT management's explanations.\n\n"
        "Rules:\n"
        "* Use the metrics when answering numeric and trend questions.\n"
        "* Use the text excerpts for qualitative, descriptive, or explanatory questions.\n"
        "* For questions about 'reasons', 'explanations', 'why', 'factors', or 'management's perspective', "
        "look for content from Management Discussion sections, not just financial statements or auditor reports.\n"
        "* If the text excerpts contain Management Discussion content, use it to answer management-related questions.\n"
        "* If the answer is not clearly supported by either the metrics or the excerpts, say you do NOT have that information in this document.\n"
        "* Do NOT invent numbers or facts that are not in the provided context.\n"
        "* Do NOT use external internet or prior knowledge; only rely on this document."
    )
    
    rl = payload.role.lower()
    if "ceo" in rl:
        system_prompt += (
            "\n\nThe user's role is: CEO/top management. Focus on high-level insights, key risks, and implications."
        )
    elif "analyst" in rl:
        system_prompt += (
            "\n\nThe user's role is: Analyst. You can include more detailed breakdowns and commentary."
        )
    else:
        system_prompt += (
            "\n\nThe user's role is: Senior management. Provide an executive summary with some key numbers."
        )
    
    # Compose final user prompt for Gemini
    fiscal_info = f" (Fiscal Year: {fiscal_year})" if fiscal_year else ""
    
    # Build metrics block
    metrics_block = ""
    if data_context and data_context != "No financial data available.":
        metrics_block = f"Structured financial metrics extracted from this document:\n{data_context}\n\n"
    
    # Build RAG text block
    rag_block = ""
    if text_context:
        rag_block = (
            "Relevant text excerpts from the uploaded PDF (these are direct or near-direct extracts):\n"
            f"{text_context}\n\n"
        )
    
    full_user_prompt = f"""Company: {company_name}{fiscal_info}
Role: {payload.role}

{metrics_block}{rag_block}Based ONLY on the above metrics and text excerpts, answer the user's question.

User's question: {user_question}

Important: If the question asks about something not clearly mentioned in either the metrics or text excerpts above, 
say "I don't have that information from this document." Do not make up facts or numbers.
"""
    
    llm_answer = call_llm(system_prompt, full_user_prompt)
    
    # Build chart_data only if user explicitly asked for visualization
    chart_data = None
    if wants_visualization and metrics_by_year:
        try:
            plan = plan_chart_config(user_question, metrics_by_year)
            if plan.get("wants_chart"):
                chart_data_dict = build_chart_data_from_plan(plan, metrics_by_year)
                if chart_data_dict:
                    # Convert dict to ChartData model
                    from app.schemas import ChartData, ChartSeries
                    chart_data = ChartData(
                        chart_type=chart_data_dict["chart_type"],
                        years=chart_data_dict["years"],
                        series=[ChartSeries(**s) for s in chart_data_dict["series"]]
                    )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error building chart data: {e}")
            # Continue without chart_data - chat still works
    
    return ChatResponse(answer=llm_answer, chart_data=chart_data)


def _build_chart_data(years: List[int], metrics: Dict[str, Dict[int, float]]) -> ChartData | None:
    """
    Build ChartData from years and metrics dict.
    Includes all available metrics: revenue, net_profit, total_assets, total_liabilities.
    """
    if not years:
        return None
    
    sorted_years = sorted(years)
    series = []
    
    # Add revenue if available
    if "revenue" in metrics and metrics["revenue"]:
        series.append(
            ChartSeries(
                label="Revenue",
                values=[metrics["revenue"].get(y, 0.0) for y in sorted_years],
            )
        )
    
    # Add net_profit if available
    if "net_profit" in metrics and metrics["net_profit"]:
        series.append(
            ChartSeries(
                label="Net Profit",
                values=[metrics["net_profit"].get(y, 0.0) for y in sorted_years],
            )
        )
    
    # Add total_assets if available
    if "total_assets" in metrics and metrics["total_assets"]:
        series.append(
            ChartSeries(
                label="Total Assets",
                values=[metrics["total_assets"].get(y, 0.0) for y in sorted_years],
            )
        )
    
    # Add total_liabilities if available
    if "total_liabilities" in metrics and metrics["total_liabilities"]:
        series.append(
            ChartSeries(
                label="Total Liabilities",
                values=[metrics["total_liabilities"].get(y, 0.0) for y in sorted_years],
            )
        )
    
    if not series:
        return None
    
    return ChartData(years=sorted_years, series=series)
