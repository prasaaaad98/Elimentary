from app.database import Base, engine, SessionLocal
from app.models import Company, FinancialMetric


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Example company
    ril = Company(code="RIL_CONSOLIDATED", name="Reliance Industries Ltd (Consolidated)")

    existing = db.query(Company).filter_by(code=ril.code).first()
    if not existing:
        db.add(ril)
        db.commit()
        db.refresh(ril)
    else:
        ril = existing

    # Dummy metrics – replace with real numbers from AR when you have time
    demo_metrics = [
        (2022, "revenue", 700000.0),
        (2023, "revenue", 800000.0),
        (2024, "revenue", 900000.0),
        (2022, "net_profit", 60000.0),
        (2023, "net_profit", 65000.0),
        (2024, "net_profit", 70000.0),
    ]

    for year, name, value in demo_metrics:
        exists = (
            db.query(FinancialMetric)
            .filter_by(company_id=ril.id, year=year, metric_name=name)
            .first()
        )
        if not exists:
            db.add(
                FinancialMetric(
                    company_id=ril.id,
                    year=year,
                    metric_name=name,
                    value=value,
                    unit="INR Cr",
                )
            )

    db.commit()
    db.close()


if __name__ == "__main__":
    seed()
