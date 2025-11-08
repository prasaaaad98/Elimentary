import json
import logging
import re
from typing import List, Dict, Any

import pdfplumber
from sqlalchemy.orm import Session

from app.llm import call_llm
from app.models import Document, FinancialMetric




logger = logging.getLogger(__name__)


def _extract_json(raw: str, context: str) -> Any | None:
    """
    Try to parse JSON from an LLM string. Handles markdown fences and extra text.
    Returns parsed object or None.
    """
    raw = raw.strip()
    # Try direct parse
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Try to find a JSON object substring
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        candidate = m.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            logger.exception("Failed to parse JSON candidate for %s", context)

    logger.error("Could not parse JSON for %s. Raw response: %r", context, raw[:500])
    return None


def _find_pages_with_keywords(pdf: pdfplumber.PDF, keywords: List[str]) -> List[int]:
    indices: List[int] = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lower = text.lower()
        if any(kw.lower() in lower for kw in keywords):
            indices.append(i)
    return indices


def parse_pdf_and_populate_metrics(doc: Document, db: Session) -> None:
    """
    Parse a balance sheet / annual report PDF and populate:
    - doc.company_name, doc.fiscal_year
    - FinancialMetric rows (document_id-based) for:
      revenue, net_profit, total_assets, total_liabilities
    """
    logger.info("Parsing PDF for document id=%s, path=%s", doc.id, doc.storage_path)

    try:
        with pdfplumber.open(doc.storage_path) as pdf:
            pages = pdf.pages

            # 1) Meta (company, period) from first 2-3 pages
            first_pages_text = "\n\n".join(
                (pages[i].extract_text() or "") for i in range(min(3, len(pages)))
            )

            meta_system = (
                "You are reading the cover/intro pages of an annual report or balance sheet. "
                "Extract structured metadata."
            )
            meta_user = f"""
Here is the text from the first pages of an annual report:

\"\"\"{first_pages_text}\"\"\"

Return ONLY valid JSON with the following keys:
- company_name: string
- financial_year: string (e.g. "FY 2023-24" or "Year ended 31 March 2024")

Example:
{{
  "company_name": "Example Corp Ltd",
  "financial_year": "Year ended 31 March 2024"
}}
"""
            meta_raw = call_llm(meta_system, meta_user)
            meta = _extract_json(meta_raw, "company meta")
            if isinstance(meta, dict):
                doc.company_name = meta.get("company_name") or doc.company_name
                doc.fiscal_year = meta.get("financial_year") or doc.fiscal_year
                db.add(doc)
                db.commit()
                logger.info(
                    "Meta parsed for doc %s: company=%r, year=%r",
                    doc.id,
                    doc.company_name,
                    doc.fiscal_year,
                )
            else:
                logger.warning("Meta JSON not parsed for doc %s", doc.id)

            # 2) Find P&L and Balance Sheet pages
            pnl_indices = _find_pages_with_keywords(
                pdf, ["statement of profit and loss", "profit and loss", "statement of profit"]
            )
            bs_indices = _find_pages_with_keywords(
                pdf, ["balance sheet", "statement of financial position"]
            )

            pnl_text = ""
            bs_text = ""

            if pnl_indices:
                # take those pages and maybe one following page
                for idx in pnl_indices:
                    pnl_text += pages[idx].extract_text() or ""
                    if idx + 1 < len(pages):
                        pnl_text += "\n\n" + (pages[idx + 1].extract_text() or "")
            else:
                logger.warning("No P&L pages detected for doc %s, using full text as fallback", doc.id)
                pnl_text = "\n\n".join(page.extract_text() or "" for page in pages[:10])

            if bs_indices:
                for idx in bs_indices:
                    bs_text += pages[idx].extract_text() or ""
                    if idx + 1 < len(pages):
                        bs_text += "\n\n" + (pages[idx + 1].extract_text() or "")
            else:
                logger.warning("No Balance Sheet pages detected for doc %s, using full text as fallback", doc.id)
                bs_text = "\n\n".join(page.extract_text() or "" for page in pages[:10])

    except Exception:
        logger.exception("Error while reading PDF for doc %s", doc.id)
        return

    # 3) Extract P&L metrics (revenue, net_profit) per year using LLM
    pnl_system = (
        "You are extracting structured financial metrics from a company's consolidated "
        "statement of profit and loss."
    )
    pnl_user = f"""
You are given text/tables from a company's consolidated statement of profit and loss:

\"\"\"{pnl_text}\"\"\"

From this text, identify for each financial year where data is clearly reported:
- total revenue (or 'Revenue from operations' / 'Total income')
- net profit (PAT) (profit for the year attributable to owners, or consolidated profit)

Return ONLY valid JSON of the form:
{{
  "metrics": [
    {{
      "year": 2022,
      "revenue": 123456.0,
      "net_profit": 7890.0
    }},
    {{
      "year": 2023,
      "revenue": ...,
      "net_profit": ...
    }}
  ]
}}

Use integer years (e.g., 2022). If a value is not clearly available, omit that year.
Values should be numeric (floats), no commas or currency symbols.
"""

    pnl_raw = call_llm(pnl_system, pnl_user)
    pnl = _extract_json(pnl_raw, "P&L metrics")

    # Helper to insert metrics
    def insert_metric(year: int, name: str, value: float, unit: str = "INR"):
        if value is None:
            return
        try:
            v = float(value)
        except Exception:
            return
        fm = FinancialMetric(
            document_id=doc.id,
            year=year,
            metric_name=name,
            value=v,
            unit=unit,
        )
        db.add(fm)

    if isinstance(pnl, dict):
        for item in pnl.get("metrics", []):
            year = item.get("year")
            if not isinstance(year, int):
                continue
            insert_metric(year, "revenue", item.get("revenue"))
            insert_metric(year, "net_profit", item.get("net_profit"))
        db.commit()
        logger.info("Inserted P&L metrics for doc %s", doc.id)
    else:
        logger.warning("P&L JSON not parsed for doc %s", doc.id)

    # 4) Extract Balance Sheet metrics (assets, liabilities) per year
    bs_system = (
        "You are extracting structured financial metrics from a company's consolidated balance sheet."
    )
    bs_user = f"""
You are given text/tables from a company's consolidated balance sheet:

\"\"\"{bs_text}\"\"\"

From this text, identify for each financial year where data is clearly reported:
- total assets
- total liabilities (including non-current and current, but not equity)

Return ONLY valid JSON of the form:
{{
  "metrics": [
    {{
      "year": 2022,
      "total_assets": 111111.0,
      "total_liabilities": 99999.0
    }},
    {{
      "year": 2023,
      "total_assets": ...,
      "total_liabilities": ...
    }}
  ]
}}

Use integer years (e.g., 2022). If a value is not clearly available, omit that year.
Values should be numeric (floats), no commas or currency symbols.
"""

    bs_raw = call_llm(bs_system, bs_user)
    bs = _extract_json(bs_raw, "Balance Sheet metrics")

    if isinstance(bs, dict):
        for item in bs.get("metrics", []):
            year = item.get("year")
            if not isinstance(year, int):
                continue
            insert_metric(year, "total_assets", item.get("total_assets"))
            insert_metric(year, "total_liabilities", item.get("total_liabilities"))
        db.commit()
        logger.info("Inserted Balance Sheet metrics for doc %s", doc.id)
    else:
        logger.warning("Balance Sheet JSON not parsed for doc %s", doc.id)
