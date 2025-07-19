# ingestion/test_qdrant.py

from qdrant_database import QdrantManager

query = "startup"
top_k = 5

manager = QdrantManager(collection_name="docs")
results = manager.search(query, limit=top_k)

if not results:
    print("❌ No results found in Qdrant for query:", query)
else:
    print(f"✅ Top {top_k} results for query: '{query}'\n")
    for i, r in enumerate(results, 1):
        text = r.get("text", "[No text]")
        score = r.get("score", "[No score]")
        print(f"{i}. Score: {score}\n{text[:300]}\n{'-'*60}")

