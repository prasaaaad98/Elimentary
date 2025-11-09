from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    document_id: Optional[int] = None  # primary way to identify context (for uploaded PDFs)
    company_code: Optional[str] = None  # legacy/demo mode (for seeded companies)
    role: str  # "Analyst" | "CEO" | "Group Management"
    messages: List[ChatMessage]


class ChartSeries(BaseModel):
    label: str
    values: List[float]


class ChartData(BaseModel):
    chart_type: Optional[Literal["line", "bar", "pie"]] = "line"  # Default to line for backward compatibility
    years: List[int]
    series: List[ChartSeries]


class ChatResponse(BaseModel):
    answer: str
    chart_data: Optional[ChartData] = None


class UploadResponse(BaseModel):
    document_id: int
    company_name: Optional[str] = None
    fiscal_year: Optional[str] = None


class DocumentSummary(BaseModel):
    id: int
    company_name: Optional[str] = None
    fiscal_year: Optional[str] = None
    filename: str
    created_at: Optional[datetime] = None
    latest_year: Optional[int] = None
    latest_revenue: Optional[float] = None
    latest_net_profit: Optional[float] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentSummary]
