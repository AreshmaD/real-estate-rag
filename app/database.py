from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Numeric,
    Boolean,
    CheckConstraint,
    ForeignKey,
)
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

class Property(Base):
    __tablename__ = "properties"

    property_id = Column(String, primary_key=True)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)

    # Explicitly identifies fictional development records.
    is_synthetic = Column(Boolean, nullable=False)

    # Monetary values are stored as decimal amounts in USD.
    asking_price = Column(Numeric(14, 2), nullable=False)

    # None means unknown; zero means an explicitly supplied zero.
    annual_property_tax = Column(Numeric(14, 2), nullable=True)
    annual_insurance = Column(Numeric(14, 2), nullable=True)
    monthly_hoa = Column(Numeric(14, 2), nullable=True)

    # Describe where the supplied values came from.
    source_notes = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "asking_price > 0",
            name="ck_property_price_positive",
        ),
        CheckConstraint(
            "annual_property_tax IS NULL OR annual_property_tax >= 0",
            name="ck_property_tax_nonnegative",
        ),
        CheckConstraint(
            "annual_insurance IS NULL OR annual_insurance >= 0",
            name="ck_property_insurance_nonnegative",
        ),
        CheckConstraint(
            "monthly_hoa IS NULL OR monthly_hoa >= 0",
            name="ck_property_hoa_nonnegative",
        ),
    )

class PropertyDocument(Base):
    __tablename__ = "property_documents"

    id = Column(Integer, primary_key=True)

    property_id = Column(
        String,
        ForeignKey("properties.property_id"),
        nullable=False,
        index=True,
    )

    document_name = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "property_id",
            "document_name",
            name="uq_property_document",
        ),
    )

def init_db():
    Base.metadata.create_all(bind=engine)
