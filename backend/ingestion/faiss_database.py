
import os  
import time
import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

def setup_faiss_with_text_storage(nodes, embed_model_name="multi-qa-mpnet-base-dot-v1"):
    """FAISS with separate text storage for full functionality"""
    print("Setting up FAISS with separate text storage...")
    start_time = time.perf_counter()
    
    try:
        faiss_path = "./faiss_index"
        os.makedirs(faiss_path, exist_ok=True)
        
        faiss_index_file = os.path.join(faiss_path, "faiss.index")
        text_store_file = os.path.join(faiss_path, "text_store.pkl")
        embeddings_file = os.path.join(faiss_path, "embeddings.pkl")
        
        # Initialize embedding model
        embed_model = SentenceTransformer(embed_model_name)
        
        # Check if we can load existing data
        if (os.path.exists(faiss_index_file) and 
            os.path.exists(text_store_file) and 
            os.path.exists(embeddings_file)):
            
            print("Loading existing FAISS index and text store...")
            try:
                # Load FAISS index
                faiss_index = faiss.read_index(faiss_index_file)
                
                # Load text store (mapping from index to text)
                with open(text_store_file, 'rb') as f:
                    text_store = pickle.load(f)
                
                # Load embeddings
                with open(embeddings_file, 'rb') as f:
                    embeddings = pickle.load(f)
                
                print(f"Loaded FAISS index with {faiss_index.ntotal} vectors")
                print(f"Loaded text store with {len(text_store)} entries")
                
                # Create custom retriever
                retriever = FaissTextRetriever(
                    faiss_index=faiss_index,
                    text_store=text_store,
                    embeddings=embeddings,
                    embed_model=embed_model
                )
                
                setup_time = time.perf_counter() - start_time
                print(f"FAISS loaded in {setup_time:.2f}s")
                return retriever, setup_time
                
            except Exception as e:
                print(f"Failed to load existing data: {e}, recreating...")
        
        # Create new index
        print("Creating new FAISS index with text storage...")
        
        if len(nodes) == 0:
            raise ValueError("No text nodes provided to FAISS setup — cannot initialize index.")
        
        # Extract text content from nodes
        texts = []
        text_store = {}
        
        for i, node in enumerate(nodes):
            if i % 50 == 0:
                print(f"Processing node {i+1}/{len(nodes)}")
            
            # Get text content
            text_content = node.get_content() if hasattr(node, 'get_content') else str(node.text)
            texts.append(text_content)
            
            # Store text and metadata
            text_store[i] = {
                'text': text_content,
                'metadata': getattr(node, 'metadata', {}),
                'node_id': getattr(node, 'node_id', str(i))
            }
        
        # Generate embeddings using sentence-transformers
        print("Generating embeddings...")
        embeddings = embed_model.encode(texts, show_progress_bar=True)
        
        # Normalize embeddings for cosine similarity
        embeddings_normalized = []
        for embedding in embeddings:
            embedding = np.array(embedding, dtype=np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            embeddings_normalized.append(embedding)
        
        embeddings_array = np.array(embeddings_normalized)
        embed_dim = embeddings_array.shape[1]
        
        # Create FAISS index with inner product (for normalized vectors = cosine similarity)
        faiss_index = faiss.IndexFlatIP(embed_dim)
        faiss_index.add(embeddings_array)
        
        print(f"Created FAISS index with {faiss_index.ntotal} vectors")
        
        # Save everything
        faiss.write_index(faiss_index, faiss_index_file)
        
        with open(text_store_file, 'wb') as f:
            pickle.dump(text_store, f)
            
        with open(embeddings_file, 'wb') as f:
            pickle.dump(embeddings_normalized, f)
        
        print("Saved FAISS index and text store")
        
        # Create custom retriever
        retriever = FaissTextRetriever(
            faiss_index=faiss_index,
            text_store=text_store,
            embeddings=embeddings_normalized,
            embed_model=embed_model
        )
        
        setup_time = time.perf_counter() - start_time
        print(f"FAISS setup completed in {setup_time:.2f}s")
        
        return retriever, setup_time
        
    except Exception as e:
        print(f"ERROR: Failed to setup FAISS with text storage: {e}")
        import traceback
        traceback.print_exc()
        return None, 0

class FaissTextRetriever:
    """Custom retriever that combines FAISS search with text storage"""
    
    def __init__(self, faiss_index, text_store, embeddings, embed_model):
        self.faiss_index = faiss_index
        self.text_store = text_store
        self.embeddings = embeddings
        self.embed_model = embed_model
    
    def retrieve(self, query, top_k=10):
        """Retrieve similar documents with full text content"""
        try:
            # Get and normalize query embedding
            query_embedding = self.embed_model.encode([query])[0]
            query_embedding = np.array(query_embedding, dtype=np.float32)
            norm = np.linalg.norm(query_embedding)
            if norm > 0:
                query_embedding = query_embedding / norm
            
            # Search FAISS index
            query_embedding = query_embedding.reshape(1, -1)
            scores, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Build results with text content
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.text_store):  # Valid index check
                    text_data = self.text_store[idx]
                    
                    # Create a NodeWithScore-like object
                    result = type('NodeWithScore', (), {
                        'text': text_data['text'],
                        'metadata': text_data.get('metadata', {}),
                        'node_id': text_data.get('node_id', str(idx)),
                        'score': float(score),
                        'get_content': lambda: text_data['text']
                    })()
                    
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error in FAISS retrieval: {e}")
            return []