from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # e.g. "RIL_CONSOLIDATED"
    name = Column(String, nullable=False)

    metrics = relationship("FinancialMetric", back_populates="company")


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    year = Column(Integer, index=True)
    metric_name = Column(String, index=True)  # e.g. "revenue", "net_profit"
    value = Column(Float)
    unit = Column(String, default="INR Cr")

    company = relationship("Company", back_populates="metrics")
