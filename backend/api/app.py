# api/app.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import defaultdict

from response_generator.generator import ResponseGenerator
from ingestion.faiss_database import setup_faiss_with_text_storage
from preprocessor.profanity_check import check_profanity

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chat history for context retention
chat_histories = defaultdict(list)

# Setup RAG pipeline
generator = ResponseGenerator()
faiss_retriever, _ = setup_faiss_with_text_storage([])
generator.load_faiss(faiss_retriever)

# Input/output models
class ChatRequest(BaseModel):
    query: str
    username: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user = request.username
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Empty query not allowed")

    if check_profanity(query):
        return ChatResponse(response="⚠️ Please avoid using offensive language.")

    chat_histories[user].append({"role": "user", "content": query})

    response_data = generator.generate(query)
    reply = response_data["answer"]

    chat_histories[user].append({"role": "assistant", "content": reply})
    chat_histories[user] = chat_histories[user][-20:]  # Limit memory use

    return ChatResponse(response=reply)

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Backend is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
