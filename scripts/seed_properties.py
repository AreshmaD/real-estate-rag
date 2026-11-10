from decimal import Decimal

from app.database import Property, SessionLocal, init_db


SAMPLE_PROPERTIES = [
    {
        "property_id": "SYN-001",
        "address": "101 Example Lane",
        "city": "Demo Harbor",
        "state": "XX",
        "is_synthetic": True,
        "asking_price": Decimal("350000.00"),
        "annual_property_tax": Decimal("4800.00"),
        "annual_insurance": Decimal("1800.00"),
        "monthly_hoa": Decimal("0.00"),
        "source_notes": (
            "Fictional sample, as of 2026-11-08. "
            "syn-001-property-packet.pdf, page 1. "
            "Insurance is a nonbinding sample estimate. "
            "Taxes are scenario inputs, not predicted post-sale taxes."
        ),
    },
    {
        "property_id": "SYN-002",
        "address": "202 Sample Court",
        "city": "Demo Harbor",
        "state": "XX",
        "is_synthetic": True,
        "asking_price": Decimal("325000.00"),
        "annual_property_tax": Decimal("4200.00"),
        "annual_insurance": Decimal("1500.00"),
        "monthly_hoa": Decimal("325.00"),
        "source_notes": (
            "Fictional sample, as of 2026-11-08. "
            "syn-002-property-packet.pdf, page 1; "
            "HOA uses the newer notice on page 4, effective 2026-11-01. "
            "The older listing shows $250. "
            "Insurance is a nonbinding sample estimate."
        ),
    },
    {
        "property_id": "SYN-003",
        "address": "303 Fixture Drive",
        "city": "Demo Harbor",
        "state": "XX",
        "is_synthetic": True,
        "asking_price": Decimal("375000.00"),
        "annual_property_tax": Decimal("5400.00"),
        "annual_insurance": None,
        "monthly_hoa": Decimal("50.00"),
        "source_notes": (
            "Fictional sample, as of 2026-11-08. "
            "syn-003-property-packet.pdf, pages 1 and 4. "
            "Insurance is missing and must remain unknown."
        ),
    },
]


def seed_properties():
    init_db()
    inserted = 0
    skipped = 0

    with SessionLocal.begin() as session:
        for values in SAMPLE_PROPERTIES:
            existing = session.get(
                Property, values["property_id"]
            )

            if existing is not None:
                skipped += 1
                continue

            session.add(Property(**values))
            inserted += 1

    print(f"Inserted: {inserted}; skipped existing: {skipped}")


if __name__ == "__main__":
    seed_properties()