import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime

# Document processing imports
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, UpdateStatus
)
from dotenv import load_dotenv
from process_files import Parser
#from ingestion.process_files import Parser
# Load environment variables
load_dotenv()

class QdrantManager:
    """
    Simple Qdrant Vector Database Manager
    Handles document processing and basic CRUD operations
    """
    def __init__(self,
                collection_name: str,  # Required for cloud
                embedding_model: str = "all-MiniLM-L6-v2",
                qdrant_url: Optional[str] = None,
                qdrant_api_key: Optional[str] = None):
        """
        Initialize Qdrant Manager for Cloud
        Args:
            collection_name: REQUIRED collection name
            embedding_model: Model name (default: all-MiniLM-L6-v2)
            qdrant_url: Cloud URL (optional if in .env)
            qdrant_api_key: API key (optional if in .env)
        """
        # 1. Load environment variables (prioritizing .env)
        load_dotenv(override=True)  # Load even if variables already set
        
        # 2. Configure connection parameters
        self.collection_name = collection_name
        self.qdrant_url = (
            qdrant_url 
            or os.getenv("QDRANT_URL") 
            or "https://ab1a28a4-8c5e-4483-bd7f-59bc400e25a0.europe-west3-0.gcp.cloud.qdrant.io"  # Default fallback
        )
        self.qdrant_api_key = (
            qdrant_api_key 
            or os.getenv("QDRANT_API_KEY") 
            or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.UTbNfnmUXj_I6uNQec82uJqoFj71kDi1NPeEihxWBvA"  # Default fallback
        )
        
        # 3. Validate critical parameters
        if not all([self.collection_name, self.qdrant_url, self.qdrant_api_key]):
            missing = []
            if not self.collection_name: missing.append("collection_name")
            if not self.qdrant_url: missing.append("QDRANT_URL")
            if not self.qdrant_api_key: missing.append("QDRANT_API_KEY")
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}\n"
                "Provide these either as arguments or in .env file"
            )
        
        # 4. Initialize models and connection
        try:
            self.embedding_model = SentenceTransformer(embedding_model)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            
            # 5. Configure cloud connection
            self.client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key,
                timeout=30.0,
                prefer_grpc=True,  # Recommended for cloud
                https=True  # Force HTTPS
            )
            
            # 6. Test connection immediately
            self.client.get_collections()  # Will raise exception if connection fails
            print(f"✅ Connected to Qdrant Cloud at {self.qdrant_url}")
            
            # 7. Setup collection
            self._setup_collection()
            
        except Exception as e:
            self.client = None
            raise ConnectionError(
                f"Failed to initialize Qdrant Cloud connection:\n"
                f"URL: {self.qdrant_url}\n"
                f"Error: {str(e)}"
            ) from e

    def _setup_connection(self):
        """Initialize Qdrant client connection with timeout handling"""
        try:
            print(f"Connecting to Qdrant at: {self.qdrant_url}")
            
            if self.qdrant_api_key:
                self.client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key,
                    timeout=300.0,  # Add timeout
                    prefer_grpc=False  # Use HTTP instead of gRPC
                )
            else:
                self.client = QdrantClient(
                    url=self.qdrant_url,
                    timeout=30.0,
                    prefer_grpc=False
                )

            # Test connection
            collections = self.client.get_collections()
            print(f"✅ Connected successfully. Found {len(collections.collections)} collections")
            
        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {e}")
            # Don't raise exception - allow graceful degradation
            self.client = None

    def _setup_collection(self):
        """Create or verify collection setup"""
        if not self.client:
            print("⚠️ Skipping collection setup - no Qdrant connection")
            return
            
        try:
            # Check if collection exists
            try:
                collection_info = self.client.get_collection(self.collection_name)
                print(f"Using existing collection: {self.collection_name}")
                return
            except Exception:
                pass  # Collection doesn't exist, create it

            # Create new collection
            print(f"Creating new collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            print(f"Collection '{self.collection_name}' created successfully")
            
        except Exception as e:
            print(f"Failed to setup collection: {e}")
            self.client = None

    def store_documents(self, chunks: List[Dict], batch_size: int = 30) -> bool:
        """Store document chunks in Qdrant"""
        if not chunks:
            print("No chunks to store")
            return False

        if not self.client:
            print("❌ Cannot store documents - no Qdrant connection")
            return False

        try:
            # Generate embeddings
            print("Generating embeddings...")
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

            # Prepare points for insertion
            points = []
            for chunk, embedding in zip(chunks, embeddings):
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding.tolist(),
                    payload={**chunk, 'stored_at': datetime.now().isoformat()}
                )
                points.append(point)

            # Insert in batches
            print(f"Storing {len(points)} points...")
            for i in range(0, len(points), batch_size):
                batch_points = points[i:i + batch_size]
                result = self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points,
                    wait=True
                )
                
                if result.status != UpdateStatus.COMPLETED:
                    print(f"Failed to store batch {i // batch_size + 1}")
                    return False

            print(f"✅ Successfully stored all {len(points)} documents")
            return True
            
        except Exception as e:
            print(f"Storage operation failed: {e}")
            return False

    def search(self,
               query: str,
               limit: int = 5,
               score_threshold: Optional[float] = None,
               filter_conditions: Optional[Dict] = None) -> List[Dict]:
        """Search for similar documents"""
        if not self.client:
            print("⚠️ Cannot search - no Qdrant connection")
            return []
            
        try:
            # Generate query embedding
            query_vector = self.embedding_model.encode([query])[0]

            # Prepare filter if provided
            search_filter = None
            if filter_conditions:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        ) for key, value in filter_conditions.items()
                    ]
                )

            # Perform search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )

            # Format results
            results = []
            for hit in search_result:
                results.append({
                    'id': hit.id,
                    'score': hit.score,
                    'text': hit.payload.get('text', ''),
                    'source': hit.payload.get('source', ''),
                    'file_type': hit.payload.get('file_type', ''),
                    'metadata': hit.payload
                })
            return results
            
        except Exception as e:
            print(f"Search failed: {e}")
            return []


def main():
    """Main function for testing the QdrantManager"""
    print("Qdrant Manager - Interactive Mode")
    print("=" * 165)

    # Initialize the Qdrant manager
    collection_name = "docs"
    manager = QdrantManager(collection_name=collection_name)
    
    # Initialize the Parser from BBCB_modules
    parser = Parser()

    # Example file processing
    file_path = "M1 - Why Startups Fail.pdf"
    if file_path and os.path.exists(file_path):
        # Process the document with a sample question
        text, images, transcript, answer, video_clip, matched_content = parser.process_document(
            uploaded_file=file_path,
            gdrive_url=None,
            question="What is the main content of this document?"
        )
        
        # Prepare chunks for Qdrant storage
        chunks = []
        if text:
            # Split text into chunks (simplified example)
            text_chunks = [text[i:i+500] for i in range(0, len(text), 500)]
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    'text': chunk,
                    'source': file_path,
                    'file_type': 'PDF',
                    'chunk_number': i+1,
                    'total_chunks': len(text_chunks)
                })
        
        if chunks:
            print(f"Extracted {len(chunks)} chunks from the file.")
            manager.store_documents(chunks)
        else:
            print("No chunks extracted from file.")
    else:
        print("File not found or invalid path.")

    # Interactive search
    while True:
        print("\nOptions:")
        print("1. Search documents")
        print("2. Exit")
        choice = input("Enter your choice (1-2): ").strip()
        
        if choice == "1":
            query = input("Enter your search query: ").strip()
            if query:
                limit = 5
                results = manager.search(query, limit=limit)
                
                if results:
                    print(f"\nFound {len(results)} results:")
                    print("-" * 60)
                    for i, result in enumerate(results, 1):
                        print(f"{i}. ID: {result['id']}")
                        print(f"   Score: {result['score']:.3f}")
                        print(f"   Source: {result['source']} ({result['file_type']})")
                        print(f"   Text: {result['text'][:200]}...")
                        print("-" * 60)
                else:
                    print("No results found.")
            else:
                print("Please enter a search query.")
        elif choice == "2":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
