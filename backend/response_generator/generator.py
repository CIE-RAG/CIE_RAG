# response_generator/generator.py

from response_generator.retriever import Retriever
from response_generator.reranker import Reranker, loader
from response_generator.llm import mistral_llm
from ingestion.qdrant_database import QdrantManager
from ingestion.faiss_database import setup_faiss_with_text_storage


class ResponseGenerator:
    def __init__(self, use_reranker=True):
        self.qdrant_manager = None
        self.faiss_retriever = None
        self.use_reranker = use_reranker
        self.reranker = Reranker(loader) if use_reranker else None
        self.qdrant_available = False

        try:
            self.qdrant_manager = QdrantManager(collection_name="docs")
            if self.qdrant_manager.client:
                self.qdrant_available = True
                print("✅ Qdrant is available and connected.")
        except Exception as e:
            print(f"⚠️ Qdrant connection failed, will fallback to FAISS: {str(e)}")

    def load_faiss(self, retriever):
        self.faiss_retriever = retriever

    def search(self, query, top_k=5):
        results = []
        sources_used = []

        if self.qdrant_available and self.qdrant_manager:
            try:
                q_results = self.qdrant_manager.search(query, limit=top_k)
                if q_results:
                    results.extend(q_results)
                    sources_used.append("qdrant")
            except Exception as e:
                print(f"⚠️ Qdrant search failed: {str(e)}")

        if not results and self.faiss_retriever:
            try:
                f_results = self.faiss_retriever.retrieve(query, top_k=top_k)
                results.extend([{
                    "text": r.text,
                    "metadata": r.metadata,
                    "score": r.score,
                    "source": "faiss"
                } for r in f_results])
                sources_used.append("faiss")
            except Exception as e:
                print(f"⚠️ FAISS search failed: {str(e)}")

        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        results = results[:top_k]

        if self.use_reranker and self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=top_k)

        return results, sources_used

    def generate(self, query, chat_history=None, top_k=5):
        results, used = self.search(query, top_k)

        if not results:
            return {
                "query": query,
                "answer": "I couldn't find any relevant information to answer your question.",
                "sources": [],
                "used_sources": used
            }

        if chat_history:
            answer = mistral_llm.generate_response_with_history(
                query=query,
                search_results=results,
                chat_history=chat_history
            )
        else:
            answer = mistral_llm.generate_response(
                query=query,
                search_results=results
            )

        return {
            "query": query,
            "answer": answer,
            "sources": results,
            "used_sources": used
        }
