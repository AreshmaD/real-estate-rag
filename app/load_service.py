import hashlib
from pathlib import Path

from sqlalchemy import select

from app.config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.database import (
    init_db,
    SessionLocal,
    DocumentChunk,
    Property,
    PropertyDocument,
)
from app.ingest import load_documents, read_document
from app.chunking import chunk_text
from app.embed import embed_texts


class PropertyNotFoundError(ValueError):
    pass


def prepare_chunk_rows(document: dict) -> list[DocumentChunk]:
    """Prepare chunk records without writing them to the database."""
    rows = []

    for page in document["pages"]:
        chunks = chunk_text(
            page["text"],
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP,
        )

        if not chunks:
            continue

        embeddings = embed_texts(chunks)

        if len(embeddings) != len(chunks):
            raise RuntimeError(
                "Embedding count does not match chunk count."
            )

        for chunk_id, (chunk, embedding) in enumerate(
            zip(chunks, embeddings, strict=True)
        ):
            rows.append(
                DocumentChunk(
                    document_name=document["document_name"],
                    chunk_id=chunk_id,
                    page_number=page["page_number"],
                    source_type=document["source_type"],
                    text=chunk,
                    embedding=embedding,
                )
            )

    return rows


def load_all_documents():
    """Preserve the existing developer bulk-ingestion workflow."""
    init_db()

    documents = load_documents(DATA_DIR)
    inserted = 0
    skipped = 0

    with SessionLocal.begin() as session:
        for document in documents:
            existing = session.scalar(
                select(DocumentChunk.id)
                .where(
                    DocumentChunk.document_name
                    == document["document_name"]
                )
                .limit(1)
            )

            if existing is not None:
                skipped += 1
                continue

            rows = prepare_chunk_rows(document)
            session.add_all(rows)
            inserted += len(rows)

    return {
        "documents_found": len(documents),
        "chunks_inserted": inserted,
        "documents_skipped": skipped,
    }


def load_document_for_property(
    path: Path,
    property_id: str,
) -> dict:
    """Index one PDF/TXT and link it to an existing property.

    The caller provides a temporary local file. This function does not
    preserve the original file or manage HTTP uploads.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix not in {".pdf", ".txt"}:
        raise ValueError("Only PDF and TXT documents are supported.")

    if not path.is_file():
        raise ValueError("The uploaded file could not be read.")

    content = path.read_bytes()

    if not content:
        raise ValueError("The uploaded file is empty.")

    # Identity depends on both property and exact file bytes.
    # Changing only the filename does not create another copy.
    digest = hashlib.sha256()
    digest.update(property_id.encode("utf-8"))
    digest.update(b"\0")
    digest.update(content)

    document_name = f"upload-{digest.hexdigest()}{suffix}"

    with SessionLocal.begin() as session:
        # Serialize uploads for the same property in this workflow.
        property_record = session.scalar(
            select(Property)
            .where(Property.property_id == property_id)
            .with_for_update()
        )

        if property_record is None:
            raise PropertyNotFoundError("Unknown property ID.")

        existing_chunk = session.scalar(
            select(DocumentChunk.id)
            .where(DocumentChunk.document_name == document_name)
            .limit(1)
        )

        existing_link = session.scalar(
            select(PropertyDocument.id).where(
                PropertyDocument.property_id == property_id,
                PropertyDocument.document_name == document_name,
            )
        )

        if existing_chunk is not None:
            # Restore a missing link without re-embedding.
            if existing_link is None:
                session.add(
                    PropertyDocument(
                        property_id=property_id,
                        document_name=document_name,
                    )
                )

            result = {
                "status": "already_indexed",
                "property_id": property_id,
                "document_name": document_name,
                "chunks_inserted": 0,
            }

        else:
            document = read_document(path)

            if document is None:
                raise ValueError("Unsupported document format.")

            has_text = any(
                page["text"].strip()
                for page in document["pages"]
            )

            if not has_text:
                raise ValueError(
                    "No readable text was found. "
                    "Scanned PDFs require OCR, which is not supported yet."
                )

            document["document_name"] = document_name
            rows = prepare_chunk_rows(document)

            if not rows:
                raise ValueError("No searchable text chunks were created.")

            session.add_all(rows)

            if existing_link is None:
                session.add(
                    PropertyDocument(
                        property_id=property_id,
                        document_name=document_name,
                    )
                )

            result = {
                "status": "indexed",
                "property_id": property_id,
                "document_name": document_name,
                "chunks_inserted": len(rows),
            }

    # The transaction has committed successfully before returning.
    return result