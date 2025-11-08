from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Document, FinancialMetric
from app.schemas import DocumentSummary, DocumentListResponse

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    company_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    List all past uploaded balance sheets (financial documents).
    Only includes documents where is_financial_report == True.
    Optionally filter by company_name.
    """
    query = db.query(Document).filter(Document.is_financial_report == True)
    
    if company_name:
        query = query.filter(Document.company_name == company_name)
    
    # Order by created_at descending
    # Note: SQLite treats NULL as smaller than any value, so NULLs will appear last
    # Since we set default values in migration, all existing rows should have created_at
    try:
        docs = query.order_by(Document.created_at.desc()).all()
    except Exception:
        # Fallback: order by id if created_at causes issues
        docs = query.order_by(Document.id.desc()).all()
    
    summaries: list[DocumentSummary] = []
    
    for doc in docs:
        # Get all metrics for this document
        metrics = (
            db.query(FinancialMetric)
            .filter(FinancialMetric.document_id == doc.id)
            .all()
        )
        
        # Group metrics by year
        by_year: dict[int, dict[str, float]] = {}
        for m in metrics:
            year = m.year
            if year is None:
                continue
            if year not in by_year:
                by_year[year] = {}
            by_year[year][m.metric_name] = m.value
        
        # Find latest year and its metrics
        if by_year:
            latest_year = max(by_year.keys())
            latest_revenue = by_year[latest_year].get("revenue")
            latest_net_profit = by_year[latest_year].get("net_profit")
        else:
            latest_year = None
            latest_revenue = None
            latest_net_profit = None
        
        summaries.append(
            DocumentSummary(
                id=doc.id,
                company_name=doc.company_name,
                fiscal_year=doc.fiscal_year,
                filename=doc.filename,
                created_at=doc.created_at,
                latest_year=latest_year,
                latest_revenue=latest_revenue,
                latest_net_profit=latest_net_profit,
            )
        )
    
    return DocumentListResponse(documents=summaries)

