#import sys
#from app.retrieve import search_similar_chunks
#from app.generate import generate_answer

#query = "Which market shows strong rental demand?"
#if len(sys.argv) > 1:
#    query = sys.argv[1]

#results = search_similar_chunks(query)

#print(f"\nQuery: {query}\n")
#print("Top results:\n")

#for r in results:
#    print(f"Source: {r['document_name']} | Chunk: {r['chunk_id']} | Distance: {r['distance']:.4f}")
#    print(r["text"])
#    print("-" * 80)

#answer = generate_answer(query, results)

#print("\nFinal Answer:\n")
#print(answer)

import sys
from app.retrieve import search_similar_chunks
from app.generate import generate_answer

query = "Which market mentions insurance costs?"
if len(sys.argv) > 1:
    query = sys.argv[1]

results = search_similar_chunks(
    query,
    top_k=5,
    initial_k=50,
    max_chunks_per_doc=1
)

print(f"\nQuery: {query}\n")
print("Top diverse results:\n")

for r in results:
    print(
        f"Source: {r['document_name']} | "
        f"Page: {r['page_number']} | "
        f"Chunk: {r['chunk_id']} | "
        f"Hybrid Score: {float(r['hybrid_score']):.4f} | "
        f"Vector Distance: {float(r['vector_distance']):.4f} | "
        f"Keyword Score: {float(r['keyword_score']):.4f}"
    )
    print(r["text"][:300])
    print("-" * 80)

answer = generate_answer(query, results)

print("\nFinal Answer:\n")
print(answer)