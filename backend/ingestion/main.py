
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import shutil
import os
import uvicorn
import time
from typing import List, Optional
import re
'''
from qdrant_database import QdrantManager
from faiss_database import setup_faiss_with_text_storage
from llama_index.core.schema import TextNode, Document as LLDocument
from process_files import Parser
'''
from ingestion.qdrant_database import QdrantManager
from ingestion.faiss_database import setup_faiss_with_text_storage
from llama_index.core.schema import TextNode, Document as LLDocument
from ingestion.process_files import Parser

class CustomTextNode(TextNode):
    def get_content(self):
        return self.text


from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
parser = Parser()

# Initialize database managers
qdrant_manager = QdrantManager(collection_name="docs")
faiss_retriever = None

@app.get("/")
def health():
    return {"status": "Welcome to the vector database, FastAPI is running without any issues."}

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    if not text or len(text) < chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 200 characters
            sentence_end = text.rfind('.', start, end)
            if sentence_end > start + chunk_size - 200:
                end = sentence_end + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        if start >= len(text):
            break
    
    return chunks

def process_file(file_path: str, question: str = "Summarize this file") -> dict:
    """Process a single file using the parser and return extracted content"""
    try:
        text, images, transcript, answer, video_clip, matched_content = parser.process_document(
            uploaded_file=file_path,
            gdrive_url=None,
            question=question
        )
        
        result = {
            "text": text,
            "images": images,
            "transcript": transcript,
            "answer": answer,
            "video_clip": video_clip,
            "matched_content": matched_content
        }
        
        # Save video clip if exists
        if video_clip and os.path.exists(video_clip):
            result["video_clip_url"] = f"/download/{os.path.basename(video_clip)}"
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def parse_and_index_dir(upload_dir: str) -> List[LLDocument]:
    """Process all supported files in a directory and create documents for indexing"""
    documents = []
    for root, dirs, files in os.walk(upload_dir):
        for fname in files:
            file_path = os.path.join(root, fname)
            file_ext = os.path.splitext(fname)[-1].lower()
            
            if file_ext in [".pdf", ".pptx", ".docx", ".xlsx"]:
                try:
                    result = process_file(file_path)
                    if result["text"] and isinstance(result["text"], str) and result["text"].strip():
                        # Clean and chunk the text
                        cleaned_text = result["text"].strip()
                        chunks = chunk_text(cleaned_text)
                        
                        # Create a document for each chunk
                        for i, chunk in enumerate(chunks):
                            metadata = {
                                "file": fname,
                                "file_path": file_path,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "images": result["images"],
                                "transcript": result["transcript"],
                                "file_type": file_ext[1:].upper()
                            }
                            doc = LLDocument(
                                text=chunk,
                                metadata=metadata
                            )
                            documents.append(doc)
                            
                except Exception as e:
                    print(f"Error processing file {fname}: {str(e)}")
                    continue
    return documents

@app.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    question: str = Form("Summarize this file"),# Remove later, this is not needed, it is here only for ease of testing.
    index_to_qdrant: bool = Form(True),
    index_to_faiss: bool = Form(True)
):
    try:
        ext = Path(file.filename).suffix.lower()
        if ext not in [".pdf", ".pptx", ".mp4", ".avi", ".mov", ".mkv", ".docx", ".xlsx"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        upload_dir = "uploaded_files"
        os.makedirs(upload_dir, exist_ok=True)
        target_path = os.path.join(upload_dir, file.filename)

        with open(target_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        process_result = process_file(target_path, question)
        
        indexing_results = {}
        
        if index_to_qdrant and qdrant_manager.client and process_result["text"]:
            try:
                text_chunks = chunk_text(process_result["text"])
                chunks = []
                for i, chunk in enumerate(text_chunks):
                    chunks.append({
                        "text": chunk,
                        "source": file.filename,
                        "file_type": ext[1:].upper(),
                        "chunk_index": i,
                        "total_chunks": len(text_chunks),
                        "images": process_result["images"],
                        "transcript": process_result["transcript"]
                    })
                qdrant_success = qdrant_manager.store_documents(chunks)
                indexing_results["qdrant"] = f"success - {len(chunks)} chunks indexed" if qdrant_success else "failed"
            except Exception as e:
                indexing_results["qdrant"] = f"failed: {str(e)}"
        
        if index_to_faiss and process_result["text"]:
            try:
                global faiss_retriever
                documents = parse_and_index_dir(upload_dir)
                if documents:
                    nodes = []
                    for doc in documents:
                        node = CustomTextNode(
                            text=doc.text,
                            metadata=doc.metadata
                        )
                        nodes.append(node)
                    faiss_retriever, faiss_time = setup_faiss_with_text_storage(nodes)
                    indexing_results["faiss"] = f"success - {len(nodes)} nodes indexed ({faiss_time:.2f}s)"
                else:
                    indexing_results["faiss"] = "no documents to index"
            except Exception as e:
                indexing_results["faiss"] = f"failed: {str(e)}"
                import traceback
                traceback.print_exc()

        return {
            "message": "File processed successfully",
            "filename": file.filename,
            "processing_result": {
                "answer": process_result["answer"],
                "text_length": len(process_result["text"]) if process_result["text"] else 0,
                "images_count": len(process_result["images"]),
                "has_transcript": bool(process_result["transcript"]),
                "has_video_clip": bool(process_result.get("video_clip_url", False))
            },
            "indexing_results": indexing_results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_file(filename: str):
    """Endpoint to download processed files (video clips, etc.)"""
    file_path = None
    
    # Check in different possible locations
    possible_locations = [
        f"components/clips/{filename}",
        f"components/videos/{filename}",
        f"components/images/{filename}",
        f"uploaded_files/{filename}"
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            file_path = location
            break
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

@app.post("/search/")
async def search_doc(
    query: str = Form(...),
    top_k: int = Form(5),
    use_qdrant: bool = Form(True),
    use_faiss: bool = Form(True)
):
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        results = []
        sources_used = []
        
        # Try Qdrant first if enabled
        if use_qdrant and qdrant_manager.client:
            try:
                q_results = qdrant_manager.search(query=query, limit=top_k)
                if q_results:
                    results.extend([{
                        "text": r["text"],
                        "metadata": r["metadata"],
                        "score": r["score"],
                        "source": "qdrant"
                    } for r in q_results])
                    sources_used.append("qdrant")
                    print(f"Qdrant returned {len(q_results)} results")
            except Exception as e:
                print(f"Qdrant search error: {str(e)}")

        # Try FAISS if enabled and we need more results
        if use_faiss and (not results or len(results) < top_k) and faiss_retriever:
            try:
                # Get additional results needed
                additional_k = max(top_k - len(results), 1)
                f_results = faiss_retriever.retrieve(query, top_k=additional_k)
                
                if f_results:
                    results.extend([{
                        "text": r.text,
                        "metadata": r.metadata,
                        "score": r.score,
                        "source": "faiss"
                    } for r in f_results])
                    sources_used.append("faiss")
                    print(f"FAISS returned {len(f_results)} results")
            except Exception as e:
                print(f"FAISS search error: {str(e)}")

        if not results:
            return {
                "message": "No results found",
                "results": [],
                "sources_used": sources_used,
                "debug_info": {
                    "qdrant_connected": bool(qdrant_manager.client),
                    "faiss_available": bool(faiss_retriever),
                    "query": query
                }
            }

        # Sort all results by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "results": results[:top_k],
            "sources_used": sources_used,
            "total_found": len(results)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/")
async def get_status():
    """Get status of both database connections"""
    return {
        "qdrant": {
            "connected": bool(qdrant_manager.client),
            "collection": qdrant_manager.collection_name if qdrant_manager.client else None
        },
        "faiss": {
            "available": bool(faiss_retriever),
            "index_size": faiss_retriever.faiss_index.ntotal if faiss_retriever else 0
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
