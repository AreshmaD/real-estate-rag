from sqlalchemy import select

from app.config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.database import init_db, SessionLocal, DocumentChunk
from app.ingest import load_documents
from app.chunking import chunk_text
from app.embed import embed_texts


def load_all_documents():
    init_db()
    session = SessionLocal()

    documents = load_documents(DATA_DIR)
    inserted = 0
    skipped = 0

    for doc in documents:
        existing = session.execute(
            select(DocumentChunk.id).where(DocumentChunk.document_name == doc["document_name"])
        ).first()

        if existing:
            skipped += 1
            continue

        for page in doc["pages"]:
            chunks = chunk_text(
                page["text"],
                chunk_size=CHUNK_SIZE,
                overlap=CHUNK_OVERLAP
            )

            if not chunks:
                continue

            embeddings = embed_texts(chunks)

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                row = DocumentChunk(
                    document_name=doc["document_name"],
                    chunk_id=i,
                    page_number=page["page_number"],
                    source_type=doc["source_type"],
                    text=chunk,
                    embedding=embedding
                )
                session.add(row)
                inserted += 1

    session.commit()
    session.close()

    return {
        "documents_found": len(documents),
        "chunks_inserted": inserted,
        "documents_skipped": skipped
    }