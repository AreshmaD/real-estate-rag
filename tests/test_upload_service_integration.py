import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.database import (
    DocumentChunk,
    Property,
    PropertyDocument,
    engine,
)
from app.load_service import (
    PropertyNotFoundError,
    load_document_for_property,
)


@unittest.skipUnless(
    os.getenv("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 to run PostgreSQL integration tests.",
)
class UploadServiceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.addCleanup(self.connection.close)

        self.transaction = self.connection.begin()
        self.addCleanup(self.transaction.rollback)

        # Each service transaction uses a savepoint so an expected
        # failure does not roll back the outer test transaction.
        self.TestSession = sessionmaker(
            bind=self.connection,
            join_transaction_mode="create_savepoint",
        )

        self.property_ids = [
            f"UPLOAD-TEST-{uuid4().hex}",
            f"UPLOAD-TEST-{uuid4().hex}",
        ]

        with self.TestSession.begin() as session:
            for property_id in self.property_ids:
                session.add(
                    Property(
                        property_id=property_id,
                        address="Temporary upload test",
                        city="Demo Harbor",
                        state="XX",
                        is_synthetic=True,
                        asking_price=100000,
                        source_notes="Temporary test fixture.",
                    )
                )

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

        self.path = self.directory / "sample.txt"
        self.path.write_text(
            "FICTIONAL TEST DOCUMENT. "
            "A maintenance visit was reported in October 2026.",
            encoding="utf-8",
        )

        session_patch = patch(
            "app.load_service.SessionLocal",
            self.TestSession,
        )
        session_patch.start()
        self.addCleanup(session_patch.stop)

        embedding_patch = patch(
            "app.load_service.embed_texts",
            side_effect=lambda texts: [
                [1.0] + [0.0] * 383
                for _ in texts
            ],
        )
        self.embed_mock = embedding_patch.start()
        self.addCleanup(embedding_patch.stop)

    def link_names(self, property_id):
        with self.TestSession() as session:
            return set(
                session.scalars(
                    select(PropertyDocument.document_name).where(
                        PropertyDocument.property_id == property_id
                    )
                ).all()
            )

    def chunk_count(self, document_name):
        with self.TestSession() as session:
            return session.scalar(
                select(func.count())
                .select_from(DocumentChunk)
                .where(
                    DocumentChunk.document_name == document_name
                )
            )

    def test_upload_indexes_and_links_document(self):
        result = load_document_for_property(
            self.path,
            self.property_ids[0],
        )

        self.assertEqual(result["status"], "indexed")
        self.assertGreater(result["chunks_inserted"], 0)
        self.assertEqual(
            self.link_names(self.property_ids[0]),
            {result["document_name"]},
        )
        self.assertEqual(
            self.chunk_count(result["document_name"]),
            result["chunks_inserted"],
        )

    def test_renamed_duplicate_does_not_reembed(self):
        first = load_document_for_property(
            self.path,
            self.property_ids[0],
        )
        calls_after_first = self.embed_mock.call_count

        renamed = self.directory / "renamed.txt"
        renamed.write_bytes(self.path.read_bytes())

        second = load_document_for_property(
            renamed,
            self.property_ids[0],
        )

        self.assertEqual(second["status"], "already_indexed")
        self.assertEqual(second["chunks_inserted"], 0)
        self.assertEqual(
            second["document_name"],
            first["document_name"],
        )
        self.assertEqual(
            self.embed_mock.call_count,
            calls_after_first,
        )
        self.assertEqual(
            self.chunk_count(first["document_name"]),
            first["chunks_inserted"],
        )

    def test_same_content_has_separate_property_identity(self):
        first = load_document_for_property(
            self.path,
            self.property_ids[0],
        )
        second = load_document_for_property(
            self.path,
            self.property_ids[1],
        )

        self.assertNotEqual(
            first["document_name"],
            second["document_name"],
        )
        self.assertEqual(
            self.link_names(self.property_ids[0]),
            {first["document_name"]},
        )
        self.assertEqual(
            self.link_names(self.property_ids[1]),
            {second["document_name"]},
        )

    def test_empty_or_whitespace_document_is_rejected(self):
        for text in ("", "   \n\t"):
            with self.subTest(text=repr(text)):
                self.path.write_text(text, encoding="utf-8")

                with self.assertRaises(ValueError):
                    load_document_for_property(
                        self.path,
                        self.property_ids[0],
                    )

        self.assertEqual(
            self.link_names(self.property_ids[0]),
            set(),
        )
        self.embed_mock.assert_not_called()

    def test_embedding_failure_leaves_no_chunks_or_link(self):
        with self.TestSession() as session:
            before = session.scalar(
                select(func.count()).select_from(DocumentChunk)
            )

        self.embed_mock.side_effect = RuntimeError(
            "Simulated embedding failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Simulated embedding failure",
        ):
            load_document_for_property(
                self.path,
                self.property_ids[0],
            )

        with self.TestSession() as session:
            after = session.scalar(
                select(func.count()).select_from(DocumentChunk)
            )

        self.assertEqual(after, before)
        self.assertEqual(
            self.link_names(self.property_ids[0]),
            set(),
        )

    def test_unknown_property_is_rejected(self):
        with self.assertRaises(PropertyNotFoundError):
            load_document_for_property(
                self.path,
                f"MISSING-{uuid4().hex}",
            )

        self.embed_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()