# The following code defines our embedder, 
# use this to change the embedding model when it comes to the LLM response
# Observed behaviour showed using same embedding models for ingest and retrieval gave best results 
# use the models from our VectorDb reports 

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
        # CrossEncoder doesn't need tokenizer separately - make sure to check the corss encoder incase reranker is fiddled with
        return None, self.reranker_model

    def get_image_components(self):
        # Optional: extend later for image/video captioning
        return None, None
