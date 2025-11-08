import json
import logging
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime

import pdfplumber
from sqlalchemy.orm import Session

from app.llm import call_llm, embed_texts
from app.models import Document, FinancialMetric, DocumentChunk




logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> list[str]:
    """
    Simple character-based chunking with overlap. This is enough for RAG usage in this project.
    max_chars: maximum length of each chunk.
    overlap: number of characters of overlap between consecutive chunks.
    """
    text = text.strip()
    if not text:
        return []
    
    chunks: list[str] = []
    start = 0
    length = len(text)
    
    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        # Overlap
        start = max(0, end - overlap)
    
    return chunks


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


def classify_pdf_as_financial(pdf_path: str) -> Tuple[bool, str]:
    """
    Classify a PDF as financial (balance sheet/annual report) or non-financial.
    Returns (is_financial: bool, reason: str)
    """
    logger.info("Classifying PDF: %s", pdf_path)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = pdf.pages
            # Extract text from first 5 pages for classification
            # This is usually enough to determine document type
            sample_text = "\n\n".join(
                (pages[i].extract_text() or "") for i in range(min(5, len(pages)))
            )
            
            # If PDF is very short or has no text, it's likely not a financial document
            if len(sample_text.strip()) < 100:
                return False, "PDF contains insufficient text content to be a financial document"
            
            classification_system = (
                "You are a document classifier specializing in financial documents. "
                "Your task is to determine if a PDF document is a financial report (balance sheet, annual report, "
                "quarterly report, financial statements) or a non-financial document (novel, marksheet, "
                "general document, etc.). Be strict: only classify as financial if the document clearly contains "
                "financial statements, balance sheets, profit & loss statements, or annual/quarterly financial reports."
            )
            
            classification_user = f"""
Analyze the following text extracted from the first pages of a PDF document:

\"\"\"{sample_text[:5000]}\"\"\"

Determine if this is a financial document (balance sheet, annual report, financial statements) or a non-financial document.

Return ONLY valid JSON with the following structure:
{{
  "is_financial": true or false,
  "reason": "Brief explanation of why this document is or is not a financial report"
}}

Examples of financial documents:
- Annual reports with balance sheets and P&L statements
- Quarterly financial reports
- Consolidated financial statements
- Standalone financial statements

Examples of non-financial documents:
- Novels, books, literature
- Academic marksheets, certificates
- General business documents without financial data
- Marketing materials
- Legal documents (unless they contain financial statements)
- Research papers

Be strict: if the document does not clearly contain financial statements, balance sheets, or profit & loss data, classify it as non-financial.
"""
            
            classification_raw = call_llm(classification_system, classification_user)
            classification = _extract_json(classification_raw, "PDF classification")
            
            if isinstance(classification, dict):
                is_financial = classification.get("is_financial", False)
                reason = classification.get("reason", "Classification completed")
                logger.info(
                    "Classification result for %s: is_financial=%s, reason=%s",
                    pdf_path,
                    is_financial,
                    reason
                )
                return bool(is_financial), str(reason)
            else:
                # Fallback: check for common financial keywords
                sample_lower = sample_text.lower()
                financial_keywords = [
                    "balance sheet", "profit and loss", "financial statement",
                    "annual report", "revenue", "assets", "liabilities",
                    "cash flow", "statement of financial position",
                    "consolidated", "standalone"
                ]
                has_financial_keywords = any(keyword in sample_lower for keyword in financial_keywords)
                
                if has_financial_keywords:
                    return True, "Document contains financial keywords (fallback classification)"
                else:
                    return False, "Document does not appear to be a financial report (fallback classification)"
                    
    except Exception as e:
        logger.exception("Error classifying PDF %s: %s", pdf_path, e)
        # On error, be conservative and reject
        return False, f"Error analyzing PDF: {str(e)}"


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
    
    # 5) Extract full text, chunk it, and store embeddings for RAG
    try:
        # Reopen PDF to extract full text (we closed it earlier)
        with pdfplumber.open(doc.storage_path) as pdf:
            pages = pdf.pages
            
            # Extract text from all pages
            page_texts: list[str] = []
            for page in pages:
                t = page.extract_text() or ""
                page_texts.append(t)
            
            # Build chunk tuples (page_number, chunk_index, text)
            raw_chunks: list[tuple[int, int, str]] = []
            for page_idx, text in enumerate(page_texts):
                if not text.strip():
                    continue
                page_chunks = chunk_text(text)
                for ci, ch in enumerate(page_chunks):
                    raw_chunks.append((page_idx + 1, ci, ch))  # 1-based page numbers
            
            # Embed and store chunks
            if raw_chunks:
                texts_to_embed = [ch for (_, _, ch) in raw_chunks]
                try:
                    logger.info("Embedding %d chunks for document %s", len(texts_to_embed), doc.id)
                    vectors = embed_texts(texts_to_embed)
                    logger.info("Successfully embedded %d chunks for document %s", len(vectors), doc.id)
                except Exception as e:
                    # Log but don't crash the entire parse. RAG will just be unavailable.
                    logger.exception("Embedding failed for document %s: %s", doc.id, e)
                    vectors = [None] * len(raw_chunks)
                
                # Store chunks with embeddings
                for (page_num, chunk_idx, ch), emb in zip(raw_chunks, vectors):
                    dc = DocumentChunk(
                        document_id=doc.id,
                        page_number=page_num,
                        chunk_index=chunk_idx,
                        text=ch,
                        embedding=emb,  # JSON column stores list directly
                    )
                    db.add(dc)
                
                db.commit()
                logger.info("Stored %d chunks for document %s", len(raw_chunks), doc.id)
            else:
                logger.warning("No text chunks extracted for document %s", doc.id)
                
    except Exception as e:
        # Log but don't fail the entire parsing if chunking/embedding fails
        logger.exception("Error during chunking/embedding for document %s: %s", doc.id, e)
    
    # Mark document as processed after successful parsing
    doc.processed_at = datetime.utcnow()
    db.add(doc)
    db.commit()
    logger.info("Marked document %s as processed", doc.id)
