from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

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

    user_question = payload.messages[-1].content if payload.messages else ""


    normalized = "".join(
        ch for ch in user_question.lower() if ch.isalpha() or ch.isspace()
    ).strip()

    greeting_keywords = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    ]

    # If it's basically just a greeting (short and matches one of the patterns),
    # reply with a simple greeting and DO NOT call the LLM.
    if any(
        normalized == kw or normalized.startswith(kw + " ")
        for kw in greeting_keywords
    ) and len(normalized.split()) <= 5:
        greeting_answer = (
            f"Hi! I'm your financial copilot for {company.name}. "
            "You can ask me about revenue, profit, assets, liabilities, trends, "
            "or ratios based on the company's published balance sheet."
        )
        return ChatResponse(answer=greeting_answer, chart_data=None)
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
