# retriever.py
from response_generator.reranker import Reranker
class Retriever:
    def __init__(self, vector_store, reranker=None):
        self.vector_store = vector_store
        self.reranker = reranker

    def search_documents(self, query: str, top_k: int = 5, rerank: bool = False):
        results = self.vector_store.search(query, limit=top_k)
        
        if rerank:
            if not self.reranker:
                raise ValueError("Reranker instance not provided.")
            results = self.reranker.rerank(query, results, top_k=top_k)

        return results

    def format_results(self, results):
        for i, r in enumerate(results, 1):
            score = r.get('rerank_score', r.get('score', 0))
            print(f"{i}. Score: {score:.3f} | Source: {r.get('source', 'N/A')}")
            print(f"   Content: {r.get('content', r.get('text', '[No Content]'))[:200]}...")
            print("-" * 50)
