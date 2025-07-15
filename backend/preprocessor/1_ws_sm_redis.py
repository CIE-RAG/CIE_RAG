import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging
import httpx
from asyncio import Lock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App and middleware
# App Initialization and CORS for frontend-backend interaction, defaults to localhost:3000.
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WEBSOCKET_TIMEOUT = float(os.getenv("WEBSOCKET_TIMEOUT", "300"))
SESSION_EXPIRY = int(os.getenv("SESSION_EXPIRY", "86400"))
CHAT_HISTORY_FILE = "chat_history.json"

# Redis client
redis_client = None

# Active connections with lock
active_connections = {}
connection_lock = Lock()

# Temp in-memory storage
stored_users = []
stored_queries = []

# Auth simulation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Modules:To define input data formats for users and chat messages
class User(BaseModel):
    name: str
    email: str

class Message(BaseModel):
    text: str

# Simulates user auth with token-based scheme (no real JWT validation).
async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


# SessionManager:Handles all Redis-backed session lifecycle and chat storage logic
class SessionManager:
    def __init__(self):
        if not os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'w') as f:
                json.dump({}, f)

    # Makes a session in Redis, maps it to the user.
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

    async def get_session(self, session_id: str):
        session_data = await redis_client.hget(f"session:{session_id}", "data")
        return json.loads(session_data) if session_data else None

    # Reuses existing session or creates a new one.
    async def get_or_create_session(self, user_id: str, websocket: WebSocket = None):
        session_id = await redis_client.get(f"user_session:{user_id}")
        if session_id:
            session_id = session_id
            exists = await redis_client.exists(f"session:{session_id}")
            if exists:
                if websocket:
                    async with connection_lock:
                        active_connections[session_id] = websocket
                return session_id
        return await self.create_session(user_id, websocket)

    # Appends chat history and saves it to both Redis and JSON.
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

    # Stores history in chat_history.json.
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

    # Deletes session and cleans up Redis.
    async def delete_session(self, session_id: str):
        user_id = await redis_client.hget(f"session:{session_id}", "user_id")
        if user_id:
            await redis_client.delete(f"user_session:{user_id}")
        await redis_client.delete(f"session:{session_id}")

        async with connection_lock:
            active_connections.pop(session_id, None)

        logger.info(f"Deleted session: {session_id}")

    # Checks for disconnected WebSockets and cleans expired sessions every 60 seconds.
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

# Redis connection initialization
async def init_redis():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise

# Health check and user management endpoints: API root endpoint to verify Redis connection and app health.
@app.get("/")
async def health():
    try:
        await redis_client.ping()
        return {"status": "running", "redis": "connected"}
    except Exception as e:
        return {"status": "running", "redis": "disconnected", "error": str(e)}

# Simulates login and returns username as token.
@app.post("/login")
async def login(username: str):
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    return {"token": username, "user_id": username}

# Adds user info to memory.
@app.post("/user")
async def user(user: User):
    stored_users.append(user.dict())
    return {"status": "success", **user.dict()}

# Fetches all stored users.
@app.get("/user")
async def get_users():
    return {"count": len(stored_users), "users": stored_users}

# Handles user queries, stores them in memory, and returns a response.
@app.post("/user_query")
async def post_user_query(message: Message):
    query_data = {"text": message.text, "timestamp": str(datetime.now())}
    stored_queries.append(query_data)
    return {"status": "success", "response": f"Processed: {message.text}"}

# Fetches all stored user queries.
@app.get("/user_query")
async def get_user_queries():
    return {"count": len(stored_queries), "queries": stored_queries}

# LLM Query Handling
@app.post("/query")
async def handle_query(query_data: dict, user_id: str = Depends(get_current_user)):
    query = query_data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="No query provided")
    session_id = await session_manager.get_or_create_session(user_id)
    response = await get_llm_response(query)
    await session_manager.update_session(session_id, query, response)
    return {"session_id": session_id, "query": query, "response": response}

# Session History API
@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str, user_id: str = Depends(get_current_user)):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"session_id": session_id, "conversation_history": session["conversation_history"]}

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
            response = await get_llm_response(query)
            await session_manager.update_session(session_id, query, response)
            await websocket.send_json({
                "session_id": session_id,
                "query": query,
                "response": response
            })
    except WebSocketDisconnect:
        logger.info(f"Disconnected: {session_id}")
    finally:
        async with connection_lock:
            active_connections.pop(session_id, None)

# Mock LLM response
async def get_llm_response(query: str) -> str:
    await asyncio.sleep(0.1)
    return f"Echo: {query}"

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
