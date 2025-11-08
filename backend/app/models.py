from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # e.g. "RIL_CONSOLIDATED"
    name = Column(String, nullable=False)

    metrics = relationship("FinancialMetric", back_populates="company")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)  # local path to saved PDF
    company_name = Column(String, nullable=True)
    fiscal_year = Column(String, nullable=True)  # e.g. "FY 2023-24"
    company_code = Column(String, nullable=True)  # optional, for grouping/legacy
    is_financial_report = Column(Boolean, nullable=True)  # True if PDF is a financial document
    classification_reason = Column(Text, nullable=True)  # Explanation for classification decision

    metrics = relationship("FinancialMetric", back_populates="document")


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)  # nullable for document-based metrics
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # nullable for legacy company-based metrics
    year = Column(Integer, index=True)
    metric_name = Column(String, index=True)  # e.g. "revenue", "net_profit", "total_assets", "total_liabilities"
    value = Column(Float)
    unit = Column(String, default="INR Cr")

    company = relationship("Company", back_populates="metrics")
    document = relationship("Document", back_populates="metrics")
