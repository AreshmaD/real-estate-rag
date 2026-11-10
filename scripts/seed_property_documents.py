from sqlalchemy import select

from app.database import (
    DocumentChunk,
    Property,
    PropertyDocument,
    SessionLocal,
    init_db,
)


SAMPLE_LINKS = {
    "SYN-001": "syn-001-property-packet.pdf",
    "SYN-002": "syn-002-property-packet.pdf",
    "SYN-003": "syn-003-property-packet.pdf",
}


def seed_links():
    init_db()
    inserted = 0
    skipped = 0

    with SessionLocal.begin() as session:
        for property_id, document_name in SAMPLE_LINKS.items():
            if session.get(Property, property_id) is None:
                raise ValueError(
                    f"Property not found: {property_id}. "
                    "Run the property seed script first."
                )

            chunk_id = session.scalar(
                select(DocumentChunk.id)
                .where(DocumentChunk.document_name == document_name)
                .limit(1)
            )

            if chunk_id is None:
                raise ValueError(
                    f"Document not indexed: {document_name}"
                )

            existing = session.scalar(
                select(PropertyDocument.id).where(
                    PropertyDocument.property_id == property_id,
                    PropertyDocument.document_name == document_name,
                )
            )

            if existing is not None:
                skipped += 1
                continue

            session.add(
                PropertyDocument(
                    property_id=property_id,
                    document_name=document_name,
                )
            )
            inserted += 1

    print(f"Inserted links: {inserted}; skipped existing: {skipped}")


if __name__ == "__main__":
    seed_links()