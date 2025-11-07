from pydantic import BaseModel
from typing import List, Optional, Literal


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    company_code: str        # e.g. "RIL_CONSOLIDATED"
    role: str                # "Analyst" | "CEO" | "Group Management"
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
