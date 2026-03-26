from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.database import init_db, SessionLocal, DocumentChunk
from app.ingest import load_documents
from app.chunking import chunk_text
from app.embed import embed_texts


def main():
    init_db()
    session = SessionLocal()

    documents = load_documents("data/raw")

    for doc in documents:
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

    session.commit()
    session.close()
    print("Documents loaded into vector database.")


if __name__ == "__main__":
    main()