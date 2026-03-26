from fastapi import FastAPI
from pydantic import BaseModel

from app.retrieve import search_similar_chunks
from app.generate import generate_answer
from app.load_service import load_all_documents

app = FastAPI(title="Real Estate RAG Assistant")


class AskRequest(BaseModel):
    question: str


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
    results = search_similar_chunks(
        request.question,
        top_k=3,
        initial_k=50,
        max_chunks_per_doc=1,
        vector_weight=0.5,
        keyword_weight=0.5,
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
                    "preview": r["text"][:200] + ("..." if len(r["text"]) > 200 else "")
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
                "preview": r["text"][:200] + ("..." if len(r["text"]) > 200 else "")
            }
            for r in results
        ]
    }