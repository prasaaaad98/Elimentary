from app.database import SessionLocal
from app.models import FinancialMetric, Document

db = SessionLocal()

docs = db.query(Document).all()
print("Documents:")
for d in docs:
    print(f"- id={d.id}, name={d.company_name}, year={d.fiscal_year}")

rows = db.query(FinancialMetric).all()
print("\nFinancial metrics:")
for r in rows:
    print(
        f"id={r.id}, document_id={r.document_id}, company_id={r.company_id}, "
        f"year={r.year}, metric_name={r.metric_name}, value={r.value}"
    )
