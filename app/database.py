from sqlalchemy import create_engine, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import sessionmaker, declarative_base
from pgvector.sqlalchemy import Vector

from app.config import DB_URL

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, nullable=False)
    chunk_id = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    source_type = Column(String, nullable=False, default="txt")
    text = Column(Text, nullable=False)
    embedding = Column(Vector(384))

    __table_args__ = (
        UniqueConstraint("document_name", "page_number", "chunk_id", name="uq_document_chunk"),
    )


def init_db():
    Base.metadata.create_all(bind=engine)