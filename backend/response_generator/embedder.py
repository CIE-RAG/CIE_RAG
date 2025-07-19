# response_generator/embedder.py
from sentence_transformers import SentenceTransformer, CrossEncoder
import torch

class EmbeddingModelLoader:
    def __init__(self,
                 embedder_model_name="sentence-transformers/multi-qa-mpnet-base-dot-v1",
                 reranker_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.embedder_model_name = embedder_model_name
        self.reranker_model_name = reranker_model_name
        self.embedder_model = None
        self.reranker_model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load_all(self):
        # Load embedding model (used for vector store encoding)
        self.embedder_model = SentenceTransformer(self.embedder_model_name)

        # Load reranker model (cross-encoder)
        self.reranker_model = CrossEncoder(self.reranker_model_name, device=self.device)

    def get_text_components(self):
        # CrossEncoder doesn't need tokenizer separately
        return None, self.reranker_model

    def get_image_components(self):
        # Optional: extend later for image captioning
        return None, None
