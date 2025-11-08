from pydantic import BaseModel
from typing import List, Optional, Literal


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
    years: List[int]
    series: List[ChartSeries]


class ChatResponse(BaseModel):
    answer: str
    chart_data: Optional[ChartData] = None


class UploadResponse(BaseModel):
    document_id: int
    company_name: Optional[str] = None
    fiscal_year: Optional[str] = None
