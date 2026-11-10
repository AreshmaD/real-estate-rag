import os
import unittest
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.api import app
from app.database import (
    DocumentChunk,
    Property,
    PropertyDocument,
    engine,
)
from app.retrieve import search_similar_chunks


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 to run PostgreSQL integration tests.",
)
class PropertyRetrievalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.addCleanup(self.connection.close)

        self.transaction = self.connection.begin()
        self.addCleanup(self.transaction.rollback)

        self.TestSession = sessionmaker(bind=self.connection)
        self.property_id = f"TEST-{uuid4().hex}"

        with self.TestSession() as session:
            embedding = session.scalar(
                select(DocumentChunk.embedding)
                .where(DocumentChunk.embedding.is_not(None))
                .limit(1)
            )

            self.assertIsNotNone(
                embedding,
                "Ingest the sample documents before running these tests.",
            )

            self.query_vector = [
                float(value) for value in embedding
            ]

            self.chunk_count = session.scalar(
                select(func.count()).select_from(DocumentChunk)
            )

            session.add(
                Property(
                    property_id=self.property_id,
                    address="Temporary integration-test property",
                    city="Demo Harbor",
                    state="XX",
                    is_synthetic=True,
                    asking_price=100000,
                    source_notes=(
                        "Temporary fixture; rolled back after the test."
                    ),
                )
            )
            session.flush()

        for target, replacement in (
            ("app.api.SessionLocal", self.TestSession),
            ("app.retrieve.SessionLocal", self.TestSession),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

        embedding_patch = patch(
            "app.retrieve.embed_query",
            return_value=self.query_vector,
        )
        embedding_patch.start()
        self.addCleanup(embedding_patch.stop)

    def test_property_without_links_returns_no_evidence(self):
        with (
            patch("app.api.generate_answer") as generate,
            TestClient(app) as client,
        ):
            response = client.post(
                "/ask",
                json={
                    "question": "What inspection concerns are documented?",
                    "property_id": self.property_id,
                },
            )

        self.assertEqual(response.status_code, 200)

        result = response.json()

        self.assertEqual(result["sources"], [])
        self.assertEqual(
            result["answer"],
            "I could not find enough supporting evidence "
            "in the provided documents.",
        )
        generate.assert_not_called()

    def test_multiple_links_exclude_unrelated_documents(self):
        linked_documents = {
            "syn-001-property-packet.pdf",
            "syn-002-property-packet.pdf",
        }

        with self.TestSession() as session:
            indexed_documents = set(
                session.scalars(
                    select(DocumentChunk.document_name).distinct()
                ).all()
            )

            self.assertTrue(
                linked_documents <= indexed_documents,
                "Both sample property packets must be indexed.",
            )
            self.assertTrue(
                indexed_documents - linked_documents,
                "An unrelated document is needed to test exclusion.",
            )

            for document_name in linked_documents:
                session.add(
                    PropertyDocument(
                        property_id=self.property_id,
                        document_name=document_name,
                    )
                )

            session.flush()

        results = search_similar_chunks(
            "What findings are documented?",
            property_id=self.property_id,
            top_k=2,
            initial_k=self.chunk_count,
            max_chunks_per_doc=1,
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(
            {item["document_name"] for item in results},
            linked_documents,
        )


if __name__ == "__main__":
    unittest.main()