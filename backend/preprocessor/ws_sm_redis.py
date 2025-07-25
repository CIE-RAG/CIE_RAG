
import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging
from asyncio import Lock
from collections import defaultdict
from response_generator.generator import ResponseGenerator
from ingestion.faiss_database import setup_faiss_with_text_storage
from preprocessor.profanity_check import check_profanity

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App initialization
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("*")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WEBSOCKET_TIMEOUT = float(os.getenv("WEBSOCKET_TIMEOUT", "3000"))
SESSION_EXPIRY = int(os.getenv("SESSION_EXPIRY", "86400"))
CHAT_HISTORY_FILE = "chat_history.json"

"""
For the backend to work, one must always keep the Redis server running and the Redis URL must be set properly in this code.
To connect to the Redis server, you need Ubuntu WSL.
In the WSL:
    1. sudo service redis-server start
    2. redis-cli
    3. ping  --> If it returns "PONG", then the Redis server is running and connected successfully
    4. To check the session ids use 'keys *' command in the redis-cli
"""

# Redis client
redis_client = None

# Active connections with lock
active_connections = {}
connection_lock = Lock()

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

# SessionManager: Handles Redis-backed session lifecycle and chat storage
class SessionManager:
    def __init__(self):
        if not os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'w') as f:
                json.dump({}, f)

    # Creates a new session with a unique id from user_id and timestamp using the uuid format creates a session data structure
    # Makes a new redis entry for the session and sets an expiry time 
    # Also makes sure it connects the websocket 
    async def create_session(self, user_id: str, websocket: WebSocket = None):
        session_id = f"{user_id}_{uuid.uuid4()}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "conversation_history": [],
            "created_at": datetime.now().isoformat()
        }
        await redis_client.hset(f"session:{session_id}", mapping={
            "data": json.dumps(session_data),
            "user_id": user_id,
            "created_at": session_data["created_at"]
        })
        await redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
        await redis_client.set(f"user_session:{user_id}", session_id, ex=SESSION_EXPIRY)

        if websocket:
            async with connection_lock:
                active_connections[session_id] = websocket

        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session_id

    # Retrieves session data from Redis
    async def get_session(self, session_id: str):
        session_data = await redis_client.hget(f"session:{session_id}", "data")
        return json.loads(session_data) if session_data else None

    # Creates a new session for the user or retrieves an existing one if both user_id and password matches
    async def get_or_create_session(self, user_id: str, websocket: WebSocket = None):
        session_id = await redis_client.get(f"user_session:{user_id}")
        if session_id:
            session_id = session_id.decode() if isinstance(session_id, bytes) else session_id
            exists = await redis_client.exists(f"session:{session_id}")
            if exists:
                if websocket:
                    async with connection_lock:
                        active_connections[session_id] = websocket
                return session_id
        return await self.create_session(user_id, websocket)

    # Updates every new query and response in the session under the session_id
    async def update_session(self, session_id: str, query: str, response: str):
        session_data = await redis_client.hget(f"session:{session_id}", "data")
        if not session_data:
            logger.error(f"Session {session_id} not found")
            return

        session_dict = json.loads(session_data)
        session_dict["conversation_history"].append({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

        await redis_client.hset(f"session:{session_id}", "data", json.dumps(session_dict))
        await redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
        await self.save_to_json(session_id, query, response)

    # Saves chat history to a JSON file
    async def save_to_json(self, session_id: str, query: str, response: str):
        try:
            with open(CHAT_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = {}

        history.setdefault(session_id, []).append({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })

        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)

    # Deletes sessions when delete button in the ui is clicked and clears in-memory history
    async def delete_session(self, session_id: str):
        user_id = await redis_client.hget(f"session:{session_id}", "user_id")
        if user_id:
            user_id = user_id.decode() if isinstance(user_id, bytes) else user_id
            await redis_client.delete(f"user_session:{user_id}")
            chat_histories[user_id].clear()  # Clear in-memory history
        await redis_client.delete(f"session:{session_id}")

        async with connection_lock:
            active_connections.pop(session_id, None)

        logger.info(f"Deleted session: {session_id}")

    # Cleans up inactive and old sessions; Disconnects websocket connections after timeout
    async def cleanup_sessions(self):
        while True:
            try:
                async with connection_lock:
                    for session_id in list(active_connections.keys()):
                        websocket = active_connections[session_id]
                        if not getattr(websocket, "application_state", None) or not websocket.application_state.connected:
                            await self.delete_session(session_id)

                for key in await redis_client.keys("session:*"):
                    ttl = await redis_client.ttl(key)
                    if ttl == -1:
                        await redis_client.expire(key, SESSION_EXPIRY)
            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}")

            await asyncio.sleep(60)

session_manager = SessionManager()

# Redis connection initialization- wsl->redis server connection is checked
async def init_redis():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise

# Health check for status and redis
@app.get("/health")
async def health_check():
    try:
        await redis_client.ping()
        return {"status": "healthy", "message": "Backend is running", "redis": "connected"}
    except Exception as e:
        return {"status": "healthy", "message": "Backend is running", "redis": "disconnected", "error": str(e)}

# HTTP chat endpoint backup when websocket is not connecting
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user = request.username
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Empty query not allowed")

    if check_profanity(query):
        return ChatResponse(response="⚠️ Please avoid using offensive language.")

    session_id = await session_manager.get_or_create_session(user)
    chat_histories[user].append({"role": "user", "content": query})

    response_data = generator.generate(query)
    reply = response_data["answer"]

    await session_manager.update_session(session_id, query, reply)
    chat_histories[user].append({"role": "assistant", "content": reply})
    chat_histories[user] = chat_histories[user][-20:]  # Limit memory use

    return ChatResponse(response=reply)

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    session_id = await session_manager.get_or_create_session(user_id, websocket)
    await websocket.send_json({"session_id": session_id})
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query")
            if not query:
                await websocket.send_json({"error": "No query provided"})
                continue
            #checkpoint for profanity 
            if check_profanity(query):
                await websocket.send_json({"response": "⚠️ Please avoid using offensive language."})
                continue
            response_data = generator.generate(query)
            response = response_data["answer"]
            await session_manager.update_session(session_id, query, response)
            await websocket.send_json({
                "session_id": session_id,
                "query": query,
                "response": response
            })
            #chat history added under session_id in json and redis
            chat_histories[user_id].append({"role": "user", "content": query})
            chat_histories[user_id].append({"role": "assistant", "content": response})
            chat_histories[user_id] = chat_histories[user_id][-20:]  # Limit memory use
    except WebSocketDisconnect:
        logger.info(f"Disconnected: {session_id}")
    finally:
        async with connection_lock:
            active_connections.pop(session_id, None)

# Session history API
@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "conversation_history": session["conversation_history"]}

# Delete session endpoint
@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await session_manager.delete_session(session_id)
    return {"status": "success", "message": f"Session {session_id} deleted"}

@app.on_event("startup")
async def startup_event():
    await init_redis()
    asyncio.create_task(session_manager.cleanup_sessions())

@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
