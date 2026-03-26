from ollama import chat
from app.config import LLM_MODEL


def build_prompt(query: str, retrieved_chunks: list[dict]) -> str:
    context_parts = []

    for chunk in retrieved_chunks:
        source = f"[Source: {chunk['document_name']}"
        if chunk.get("page_number") is not None:
            source += f", page {chunk['page_number']}"
        source += f", chunk {chunk['chunk_id']}]"

        context_parts.append(f"{source}\n{chunk['text']}")

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a real estate research assistant.

Answer the user's question using only the provided context.
If the context does not contain enough information, say:
"I could not find enough supporting evidence in the provided documents."

When possible, mention the source document names in the answer.

Context:
{context}

Question:
{query}
"""
    return prompt.strip()


def generate_answer(query: str, retrieved_chunks: list[dict]) -> str:
    prompt = build_prompt(query, retrieved_chunks)

    response = chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response.message.content