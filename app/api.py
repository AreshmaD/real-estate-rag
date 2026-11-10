from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.retrieve import search_similar_chunks
from app.generate import generate_answer
from app.load_service import load_all_documents
from app.calculations import calculate_ownership_cost

app = FastAPI(title="Real Estate RAG Assistant")

PROPERTY_DOCUMENTS = {
    "SYN-001": "syn-001-property-packet.pdf",
    "SYN-002": "syn-002-property-packet.pdf",
    "SYN-003": "syn-003-property-packet.pdf",
}

class AskRequest(BaseModel):
    question: str
    property_id: str | None = None

class CostRequest(BaseModel):
    purchase_price: float = Field(gt=0, allow_inf_nan=False)
    down_payment: float = Field(ge=0, allow_inf_nan=False)
    annual_interest_rate_percent: float = Field(
        ge=0, allow_inf_nan=False
    )
    loan_term_years: int = Field(gt=0, strict=True)

    annual_property_tax: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    annual_insurance: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    monthly_hoa: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    monthly_mortgage_insurance: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    monthly_maintenance_reserve: float = Field(
        default=0, ge=0, allow_inf_nan=False
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
        **result
    }


@app.post("/ask")
def ask_question(request: AskRequest):
    document_name = None

    if request.property_id is not None:
        document_name = PROPERTY_DOCUMENTS.get(request.property_id)

        if document_name is None:
            raise HTTPException(
                status_code=400,
                detail="Unknown property ID.",
            )

    results = search_similar_chunks(
        request.question,
        top_k=5 if document_name else 3,
        initial_k=50,
        max_chunks_per_doc=5 if document_name else 1,
        vector_weight=0.5,
        keyword_weight=0.5,
        document_name=document_name,
    )
    if not results:
        return {
            "question": request.question,
            "answer": "I could not find enough supporting evidence in the provided documents.",
            "sources": []
        }

    best_hybrid = float(results[0]["hybrid_score"])

    if best_hybrid < 0.35:
        return {
            "question": request.question,
            "answer": "I could not find enough supporting evidence in the provided documents.",
            "sources": [
                {
                    "document_name": r["document_name"],
                    "page_number": r["page_number"],
                    "chunk_id": r["chunk_id"],
                    "source_type": r["source_type"],
                    "hybrid_score": round(float(r["hybrid_score"]), 4),
                    "vector_distance": round(float(r["vector_distance"]), 4),
                    "keyword_score": round(float(r["keyword_score"]), 4),
                    "preview": r["text"]
                }
                for r in results
            ]
        }

    answer = generate_answer(request.question, results)

    return {
        "question": request.question,
        "answer": answer,
        "sources": [
            {
                "document_name": r["document_name"],
                "page_number": r["page_number"],
                "chunk_id": r["chunk_id"],
                "source_type": r["source_type"],
                "hybrid_score": round(float(r["hybrid_score"]), 4),
                "vector_distance": round(float(r["vector_distance"]), 4),
                "keyword_score": round(float(r["keyword_score"]), 4),
                "preview": r["text"]
            }
            for r in results
        ]
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
        item.property_id for item in request.properties
    ]

    if len(property_ids) != len(set(property_ids)):
        raise HTTPException(
            status_code=422,
            detail="Each property must appear only once.",
        )

    for property_id in property_ids:
        if property_id not in PROPERTY_DOCUMENTS:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown sample property: {property_id}",
            )

    # Require consistent loan assumptions for this first version.
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