from response_generator.embedder import EmbeddingModelLoader
from PIL import Image
import torch
# Initialize and load models
loader = EmbeddingModelLoader()
loader.load_all() # Team Notes: We need to keep the embedding models in memory actively while reranker is running
# Need to change the above line once the entire RAG Pipeline is stable

# Access image captioning components
image_processor, image_model = loader.get_image_components()

# Access text reranker components
text_tokenizer, text_model = loader.get_text_components()

# class Reranker:
#     def __init__(self, model_loader: EmbeddingModelLoader):
#         self.text_tokenizer, self.text_model = model_loader.get_text_components()
#         self.image_processor, self.image_model = model_loader.get_image_components()
#         self.device = model_loader.device

#     def generate_caption(self, image_path):
#         image = Image.open(image_path).convert('RGB')
#         inputs = self.image_processor(image, return_tensors="pt").to(self.device)
#         with torch.no_grad():
#             out = self.image_model.generate(**inputs)
#         caption = self.image_processor.decode(out[0], skip_special_tokens=True)
#         return caption

#     def preprocess(self, query, results):
#         processed_results = []
#         for r in results:
#             if 'text' in r:
#                 content = r['text']
#             elif 'image' in r:
#                 try:
#                     content = self.generate_caption(r['image'])
#                 except Exception as e:
#                     content = "[Image Captioning Failed]"
#             else:
#                 content = "[Missing Content]"
#             processed_results.append({**r, 'content': content})
#         return processed_results

#     def rerank(self, query, results, top_k=None):
#         processed = self.preprocess(query, results)
#         pairs = [(query, r['content']) for r in processed]

#         inputs = self.text_tokenizer.batch_encode_plus(
#             pairs,
#             padding=True,
#             truncation=True,
#             return_tensors="pt"
#         ).to(self.device)

#         with torch.no_grad():
#             scores = self.text_model(**inputs).logits.squeeze(-1)

#         for i, r in enumerate(processed):
#             r['rerank_score'] = scores[i].item()

#         processed.sort(key=lambda x: x['rerank_score'], reverse=True)

#         if top_k:
#             return processed[:top_k]
#         return processed


class Reranker:
    def __init__(self, model_loader):
        _, self.text_model = model_loader.get_text_components()
        self.image_processor, self.image_model = model_loader.get_image_components()

    def generate_caption(self, image_path):
        image = Image.open(image_path).convert("RGB")
        inputs = self.image_processor(image, return_tensors="pt").to(self.text_model.device)
        with torch.no_grad():
            out = self.image_model.generate(**inputs)
        caption = self.image_processor.decode(out[0], skip_special_tokens=True)
        return caption

    def preprocess(self, query, results):
        processed_results = []
        for r in results:
            if "text" in r:
                content = r["text"]
            elif "image" in r:
                try:
                    content = self.generate_caption(r["image"])
                except Exception:
                    content = "[Image Captioning Failed]"
            else:
                content = "[Missing Content]"
            processed_results.append({**r, "content": content})
        return processed_results

    def rerank(self, query, results, top_k=None):
        processed = self.preprocess(query, results)
        pairs = [(query, r["content"]) for r in processed]

        scores = self.text_model.predict(pairs)

        for i, r in enumerate(processed):
            r["rerank_score"] = float(scores[i])

        processed.sort(key=lambda x: x["rerank_score"], reverse=True)

        return processed[:top_k] if top_k else processed
