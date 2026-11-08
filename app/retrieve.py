from sqlalchemy import text
from app.database import SessionLocal
from app.embed import embed_query
from app.config import TOP_K


def search_similar_chunks(
    query: str,
    top_k: int = TOP_K,
    initial_k: int = 50,
    max_chunks_per_doc: int = 1,
    vector_weight: float = 0.5,
    keyword_weight: float = 0.5,
    document_name: str | None = None,
):
    query_embedding = embed_query(query)

    vector_sql = text("""
        SELECT
            id,
            document_name,
            chunk_id,
            page_number,
            source_type,
            text,
            embedding <=> CAST(:query_embedding AS vector) AS vector_distance
        FROM document_chunks
        WHERE (
            CAST(:document_name AS TEXT) IS NULL
            OR document_name = CAST(:document_name AS TEXT)
        )
        ORDER BY embedding <=> CAST(:query_embedding AS vector)
        LIMIT :initial_k
    """)

    with SessionLocal() as session:
        vector_results = session.execute(
            vector_sql,
            {
                "query_embedding": str(query_embedding),
                "initial_k": initial_k,
                "document_name": document_name,
            },
        ).fetchall()
        
    results = [
        {
            "id": row[0],
            "document_name": row[1],
            "chunk_id": row[2],
            "page_number": row[3],
            "source_type": row[4],
            "text": row[5],
            "vector_distance": float(row[6]),
        }
        for row in vector_results
    ]

    if not results:
        return []

    # simple keyword matching
    query_terms = [
        term.lower()
        for term in query.replace("?", "").replace(",", "").split()
        if len(term) > 2
    ]

    stopwords = {"which", "what", "does", "the", "and", "are", "for", "with", "that", "this", "market", "markets"}
    query_terms = [term for term in query_terms if term not in stopwords]

    max_keyword = 1.0

    for r in results:
        text_lower = r["text"].lower()
        keyword_hits = sum(1 for term in query_terms if term in text_lower)
        r["keyword_score"] = float(keyword_hits)
        if r["keyword_score"] > max_keyword:
            max_keyword = r["keyword_score"]

    for r in results:
        semantic_score = 1.0 / (1.0 + r["vector_distance"])
        normalized_keyword = r["keyword_score"] / max_keyword if max_keyword > 0 else 0.0
        r["hybrid_score"] = (
            vector_weight * semantic_score +
            keyword_weight * normalized_keyword
        )

    results.sort(key=lambda x: x["hybrid_score"], reverse=True)

    diversified_results = []
    doc_counts = {}

    for result in results:
        doc_name = result["document_name"]
        current_count = doc_counts.get(doc_name, 0)

        if current_count < max_chunks_per_doc:
            diversified_results.append(result)
            doc_counts[doc_name] = current_count + 1

        if len(diversified_results) >= top_k:
            break

    return diversified_results