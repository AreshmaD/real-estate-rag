from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.calculations import calculate_ownership_cost
from app.database import Property, SessionLocal
from app.generate import generate_answer
from app.load_service import load_all_documents
from app.retrieve import search_similar_chunks


app = FastAPI(title="Real Estate RAG Assistant")


def get_existing_property_ids(property_ids: list[str]) -> set[str]:
    with SessionLocal() as session:
        return set(
            session.scalars(
                select(Property.property_id).where(
                    Property.property_id.in_(property_ids)
                )
            ).all()
        )


def format_sources(results: list[dict]) -> list[dict]:
    return [
        {
            "document_name": item["document_name"],
            "page_number": item["page_number"],
            "chunk_id": item["chunk_id"],
            "source_type": item["source_type"],
            "hybrid_score": round(float(item["hybrid_score"]), 4),
            "vector_distance": round(float(item["vector_distance"]), 4),
            "keyword_score": round(float(item["keyword_score"]), 4),
            "preview": item["text"],
        }
        for item in results
    ]


class AskRequest(BaseModel):
    question: str
    property_id: str | None = None


class CostRequest(BaseModel):
    purchase_price: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    down_payment: float = Field(
        ge=0,
        allow_inf_nan=False,
    )
    annual_interest_rate_percent: float = Field(
        ge=0,
        allow_inf_nan=False,
    )
    loan_term_years: int = Field(
        gt=0,
        strict=True,
    )

    annual_property_tax: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    annual_insurance: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    monthly_hoa: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    monthly_mortgage_insurance: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    monthly_maintenance_reserve: float = Field(
        default=0,
        ge=0,
        allow_inf_nan=False,
    )


class ComparisonProperty(CostRequest):
    property_id: str


class ComparisonRequest(BaseModel):
    properties: list[ComparisonProperty] = Field(
        min_length=2,
        max_length=3,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest_documents():
    result = load_all_documents()

    return {
        "status": "success",
        **result,
    }


@app.post("/ask")
def ask_question(request: AskRequest):
    property_selected = request.property_id is not None

    if property_selected:
        existing_ids = get_existing_property_ids(
            [request.property_id]
        )

        if request.property_id not in existing_ids:
            raise HTTPException(
                status_code=400,
                detail="Unknown property ID.",
            )

    results = search_similar_chunks(
        request.question,
        top_k=5 if property_selected else 3,
        initial_k=50,
        max_chunks_per_doc=5 if property_selected else 1,
        vector_weight=0.5,
        keyword_weight=0.5,
        property_id=request.property_id,
    )

    insufficient_evidence = (
        "I could not find enough supporting evidence "
        "in the provided documents."
    )

    if not results:
        return {
            "question": request.question,
            "answer": insufficient_evidence,
            "sources": [],
        }

    sources = format_sources(results)
    best_hybrid = float(results[0]["hybrid_score"])

    if best_hybrid < 0.35:
        return {
            "question": request.question,
            "answer": insufficient_evidence,
            "sources": sources,
        }

    answer = generate_answer(request.question, results)

    return {
        "question": request.question,
        "answer": answer,
        "sources": sources,
    }


@app.post("/cost-scenarios")
def create_cost_scenario(request: CostRequest):
    try:
        return calculate_ownership_cost(**request.model_dump())

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error


@app.post("/comparisons")
def compare_properties(request: ComparisonRequest):
    property_ids = [
        item.property_id
        for item in request.properties
    ]

    if len(property_ids) != len(set(property_ids)):
        raise HTTPException(
            status_code=422,
            detail="Each property must appear only once.",
        )

    existing_ids = get_existing_property_ids(property_ids)

    for property_id in property_ids:
        if property_id not in existing_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown property ID: {property_id}",
            )

    first = request.properties[0]

    for item in request.properties[1:]:
        if (
            item.annual_interest_rate_percent
            != first.annual_interest_rate_percent
            or item.loan_term_years != first.loan_term_years
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "Use the same interest rate and loan term "
                    "for every property in this comparison."
                ),
            )

    results = []

    for item in request.properties:
        inputs = item.model_dump(exclude={"property_id"})

        try:
            calculation = calculate_ownership_cost(**inputs)

        except ValueError as error:
            raise HTTPException(
                status_code=422,
                detail=f"{item.property_id}: {error}",
            ) from error

        results.append(
            {
                "property_id": item.property_id,
                "inputs": inputs,
                "calculation": calculation,
            }
        )

    return {
        "properties": results,
        "notes": [
            "Results use supplied scenario inputs, not verified quotes.",
            "Incomplete subtotals exclude unknown costs.",
            "Do not compare incomplete subtotals against complete totals.",
            "Maintenance reserves are separate from housing costs.",
            "Utilities, closing costs, and one-time repairs are excluded.",
        ],
    }


@app.get("/properties")
def list_properties():
    with SessionLocal() as session:
        properties = session.execute(
            select(Property).order_by(Property.property_id)
        ).scalars().all()

        return {
            "properties": [
                {
                    "property_id": item.property_id,
                    "address": item.address,
                    "city": item.city,
                    "state": item.state,
                    "is_synthetic": item.is_synthetic,
                    "asking_price": float(item.asking_price),
                    "annual_property_tax": (
                        None
                        if item.annual_property_tax is None
                        else float(item.annual_property_tax)
                    ),
                    "annual_insurance": (
                        None
                        if item.annual_insurance is None
                        else float(item.annual_insurance)
                    ),
                    "monthly_hoa": (
                        None
                        if item.monthly_hoa is None
                        else float(item.monthly_hoa)
                    ),
                    "source_notes": item.source_notes,
                }
                for item in properties
            ]
        }