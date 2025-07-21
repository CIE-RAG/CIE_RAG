import os
import json
import asyncio
import uuid
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocketState
import redis.asyncio as redis
from pydantic import BaseModel
from datetime import datetime
from asyncio import Lock
from collections import defaultdict
from response_generator.generator import ResponseGenerator
from ingestion.faiss_database import setup_faiss_with_text_storage
from preprocessor.profanity_check import check_profanity
from tenacity import retry, stop_after_attempt, wait_exponential
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import httpx  # Added for Kafka HTTP calls

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App initialization
app = FastAPI()

app.mount("/images", StaticFiles(directory="ingestion/components/images"), name="images")

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"],
    allow_headers=["Content-Type", "Authorization"],
)

# Constants
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WEBSOCKET_TIMEOUT = float(os.getenv("WEBSOCKET_TIMEOUT", "300"))
SESSION_EXPIRY = int(os.getenv("SESSION_EXPIRY", "86400"))
CHAT_HISTORY_FILE = "chat_history.json"

LOCAL_STORE_DIR = "Localstore"

if not os.path.exists(LOCAL_STORE_DIR):
    os.makedirs(LOCAL_STORE_DIR)

# Redis client
redis_client = None

# Active connections with lock
active_connections = {}
connection_lock = Lock()

# Chat history for context retention, keyed by session_id
chat_histories = defaultdict(list)

# Setup RAG pipeline
generator = ResponseGenerator()
faiss_retriever, _ = setup_faiss_with_text_storage([])
generator.load_faiss(faiss_retriever)

# Input/output models
class ChatRequest(BaseModel):
    query: str
    user_id: str

class ChatResponse(BaseModel):
    response: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    user_id: str
    email: str
    name: str

# SessionManager: Handles Redis-backed session lifecycle and chat storage
class SessionManager:
    def __init__(self):
        if not os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'w') as f:
                json.dump({}, f)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def create_user(self, email: str, name: str):
        user_id = str(uuid.uuid4())
        user_data = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "created_at": datetime.now().isoformat()
        }
        try:
            await redis_client.hset(f"user:{user_id}", mapping={
                "data": json.dumps(user_data),
                "email": email,
                "name": name
            })
            logger.info(f"Created user: {user_id} for email: {email}")
            return user_id
        except Exception as e:
            logger.error(f"Failed to create user in Redis: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create user")

    async def get_user(self, user_id: str):
        try:
            user_data = await redis_client.hget(f"user:{user_id}", "data")
            return json.loads(user_data) if user_data else None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            return None

    async def create_session(self, user_id: str, websocket: WebSocket = None):
        session_id = f"{user_id}_{uuid.uuid4()}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "conversation_history": [],
            "created_at": datetime.now().isoformat()
        }
        try:
            await redis_client.hset(f"session:{session_id}", mapping={
                "data": json.dumps(session_data),
                "user_id": user_id,
                "created_at": session_data["created_at"]
            })
            await redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
            # Only set user_session for HTTP sessions
            if not websocket:
                await redis_client.set(f"user_session:{user_id}", session_id, ex=SESSION_EXPIRY)
        except Exception as e:
            logger.error(f"Failed to create session for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create session")

        if websocket:
            async with connection_lock:
                active_connections[session_id] = websocket

        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session_id

    async def get_session(self, session_id: str):
        try:
            session_data = await redis_client.hget(f"session:{session_id}", "data")
            return json.loads(session_data) if session_data else None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            return None

    async def get_or_create_session(self, user_id: str, websocket: WebSocket = None):
        try:
            if websocket:
                return await self.create_session(user_id, websocket)
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
        except Exception as e:
            logger.error(f"Error in get_or_create_session for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Session management error")

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

        try:
            await redis_client.hset(f"session:{session_id}", "data", json.dumps(session_dict))
            await redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
            await self.save_to_json(session_id, query, response)
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {str(e)}")

    async def save_to_json(self, session_id: str, query: str, response: str):
        user_id = session_id.split("_")[0]
        user_file = os.path.join(LOCAL_STORE_DIR, f"{user_id}.json")

        try:
            if os.path.exists(user_file):
                with open(user_file, 'r') as f:
                    history = json.load(f)
            else:
                history = {}

            history.setdefault(session_id, []).append({
                "query": query,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })

            with open(user_file, 'w') as f:
                json.dump(history, f, indent=4)

        except Exception as e:
            logger.error(f"Failed to save chat to {user_file}: {str(e)}")
        
    async def remove_from_json(self, session_id: str):
        user_id = session_id.split("_")[0]
        user_file = os.path.join(LOCAL_STORE_DIR, f"{user_id}.json")

        if not os.path.exists(user_file):
            return

        try:
            with open(user_file, 'r') as f:
                history = json.load(f)

            history.pop(session_id, None)

            with open(user_file, 'w') as f:
                json.dump(history, f, indent=4)

            logger.info(f"Removed session {session_id} from {user_file}")

        except Exception as e:
            logger.error(f"Failed to remove session {session_id} from {user_file}: {str(e)}")

    async def get_latest_session_history(self, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Return the latest history for a session (up to `limit` Q&A pairs),
        formatted as alternating 'user' and 'assistant' roles.
        """
        try:
            # Pull from Redis session data
            session_data = await redis_client.hget(f"session:{session_id}", "data")
            if not session_data:
                return []

            session_dict = json.loads(session_data)
            conversation = session_dict.get("conversation_history", [])

            # Format as role-content dicts
            history = []
            for turn in conversation[-limit:]:
                history.append({"role": "user", "content": turn["query"]})
                history.append({"role": "assistant", "content": turn["response"]})

            return history[-(limit*2):]  # last 5 pairs = 10 entries max
        except Exception as e:
            logger.error(f"Error fetching session history for {session_id}: {str(e)}")
            return []

    async def load_history_from_json(self, session_id: str):
        user_id = session_id.split("_")[0]
        user_file = os.path.join(LOCAL_STORE_DIR, f"{user_id}.json")

        if not os.path.exists(user_file):
            return []

        try:
            with open(user_file, 'r') as f:
                all_sessions = json.load(f)
            session_history = all_sessions.get(session_id, [])
            # Format to chat-style history
            formatted = []
            for item in session_history:
                formatted.append({"role": "user", "content": item["query"]})
                formatted.append({"role": "assistant", "content": item["response"]})
            return formatted[-10:]  # Limit context window
        except Exception as e:
            logger.error(f"Failed to load history from {user_file}: {str(e)}")
            return []

    async def delete_session(self, session_id: str):
        try:
            user_id = await redis_client.hget(f"session:{session_id}", "user_id")
            if user_id:
                user_id = user_id.decode() if isinstance(user_id, bytes) else user_id
                remaining_sessions = [key async for key in redis_client.scan_iter(f"session:*{user_id}*")]
                if len(remaining_sessions) <= 1:
                    await redis_client.delete(f"user_session:{user_id}")
            await redis_client.delete(f"session:{session_id}")
            chat_histories[session_id].clear()
            await self.remove_from_json(session_id)
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {str(e)}")

        async with connection_lock:
            active_connections.pop(session_id, None)

        logger.info(f"Deleted session: {session_id}")

    async def cleanup_sessions(self):
        while True:
            try:
                async with connection_lock:
                    for session_id in list(active_connections.keys()):
                        websocket = active_connections[session_id]
                        try:
                            if websocket.application_state != WebSocketState.CONNECTED:
                                await self.delete_session(session_id)
                        except Exception as e:
                            logger.error(f"Cleanup error for session {session_id}: {str(e)}")
                            continue
            except Exception as e:
                logger.error(f"Unexpected cleanup error: {str(e)}")

            await asyncio.sleep(60)

session_manager = SessionManager()

# Redis connection initialization
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def init_redis():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis_client.ping()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise HTTPException(status_code=500, detail="Redis connection failed")

# Health check
@app.get("/health")
async def health_check():
    try:
        await redis_client.ping()
        return {"status": "healthy", "message": "Backend is running", "redis": "connected"}
    except Exception as e:
        return {"status": "healthy", "message": "Backend is running", "redis": "disconnected", "error": str(e)}

# Explicit OPTIONS handler for /login
@app.options("/login")
async def options_login():
    return {"status": "ok"}

# Login endpoint to generate unique user ID
@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    logger.info(f"Received POST /login with email: {request.email}")
    if not request.email or not request.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    # Validate SRN format (13 characters, starts with "PES")
    if len(request.email) != 13 or not request.email.upper().startswith("PES"):
        raise HTTPException(status_code=400, detail="SRN must be 13 characters starting with 'PES'")
    
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Use the email as the name to ensure consistency with frontend validation
    name = request.email
    try:
        user_id = await session_manager.create_user(request.email, name)
        logger.info(f"Login successful for user_id: {user_id}")
        return LoginResponse(user_id=user_id, email=request.email, name=name)
    except Exception as e:
        logger.error(f"Login failed for {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# HTTP chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_id = request.user_id
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Empty query not allowed")

    if check_profanity(query):
        return ChatResponse(response="⚠️ Please avoid using offensive language.")

    session_id = await session_manager.get_or_create_session(user_id)

    if session_id not in chat_histories or not chat_histories[session_id]:
        chat_histories[session_id] = await session_manager.load_history_from_json(session_id)

    history = chat_histories[session_id][-10:]  # last 5 Q&A pairs
    response_data = generator.generate(query, chat_history=history)
    reply = response_data["answer"]

    await session_manager.update_session(session_id, query, reply)
    chat_histories[session_id].append({"role": "user", "content": query})
    chat_histories[session_id].append({"role": "assistant", "content": reply})
    chat_histories[session_id] = chat_histories[session_id][-20:]  # maintain window

    return ChatResponse(response=reply)

# WebSocket endpoint with Kafka integration
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    try:
        # Add delay to mitigate timing issues
        await asyncio.sleep(1)
        await websocket.accept()
        session_id = await session_manager.create_session(user_id, websocket)
        logger.info(f"WebSocket connection established for session: {session_id}")
        await websocket.send_json({"session_id": session_id})
    except Exception as e:
        logger.error(f"WebSocket connection failed for user {user_id}: {str(e)}")
        return

    try:
        async with httpx.AsyncClient() as client:
            while True:
                data = await websocket.receive_json()
                query = data.get("query")
                if not query:
                    await websocket.send_json({"error": "No query provided"})
                    continue
                if check_profanity(query):
                    await websocket.send_json({"response": "⚠️ Please avoid using offensive language."})
                    continue

                # Load chat history for context
                if session_id not in chat_histories or not chat_histories[session_id]:
                    chat_histories[session_id] = await session_manager.load_history_from_json(session_id)

                # Step 1: Send query to producer_service with retries
                message_id = str(uuid.uuid4())
                query_data = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "message_id": message_id,
                    "type": "query",
                    "message": query
                }
                producer_url = "http://localhost:8000/send_message"  # Match original main.py
                producer_response = None
                for attempt in range(3):  # Retry 3 times
                    try:
                        logger.info(f"Attempting to send query to {producer_url}, attempt {attempt + 1}")
                        producer_response = await client.post(
                            producer_url,
                            headers={"accept": "application/json", "Content-Type": "application/json"},
                            json=query_data
                        )
                        if producer_response.status_code == 200:
                            logger.info(f"Query sent to producer: {query_data}")
                            break
                        else:
                            logger.warning(f"Failed to send query to {producer_url}: {producer_response.status_code}")
                    except httpx.RequestError as e:
                        logger.error(f"Connection error to {producer_url}: {str(e)}")
                        if attempt == 2:
                            logger.error(f"All retries failed for {producer_url}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                if not producer_response or producer_response.status_code != 200:
                    await websocket.send_json({"error": "Failed to send query to producer after all retries"})
                    continue

                # Step 2: Fetch query from consumer_service
                consumer_response = None
                consumer_url = "http://localhost:8001/messages"
                for attempt in range(3):  # Retry 3 times
                    try:
                        logger.info(f"Attempting to fetch query from {consumer_url}, attempt {attempt + 1}")
                        consumer_response = await client.get(
                            consumer_url,
                            params={"topic": "query", "limit": 1, "latest": True}
                        )
                        if consumer_response.status_code == 200:
                            break
                        else:
                            logger.warning(f"Failed to fetch query from {consumer_url}: {consumer_response.status_code}")
                    except httpx.RequestError as e:
                        logger.error(f"Connection error to {consumer_url}: {str(e)}")
                        if attempt == 2:
                            logger.error(f"All retries failed for {consumer_url}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                if not consumer_response or consumer_response.status_code != 200:
                    await websocket.send_json({"error": "Failed to fetch query from consumer"})
                    continue
                consumer_data = consumer_response.json()
                if consumer_data["count"] == 0 or consumer_data["messages"][0]["value"]["message_id"] != message_id:
                    await websocket.send_json({"error": "Query not found in consumer"})
                    continue
                logger.info(f"Query fetched from consumer: {consumer_data}")

                # Step 3: Generate response using ResponseGenerator with chat history
                history = chat_histories[session_id][-10:]  # last 5 Q&A pairs
                response_data = generator.generate(query, chat_history=history)
                response = response_data["answer"]

                # Step 4: Update session with query and response
                await session_manager.update_session(session_id, query, response)
                chat_histories[session_id].append({"role": "user", "content": query})
                chat_histories[session_id].append({"role": "assistant", "content": response})
                chat_histories[session_id] = chat_histories[session_id][-20:]

                # Step 5: Send answer to producer_service with retries
                answer_data = {
                    "session_id": session_id,
                    "user_id": user_id,
                    "message_id": message_id,
                    "type": "answer",
                    "message": response
                }
                producer_answer_response = None
                for attempt in range(3):  # Retry 3 times
                    try:
                        logger.info(f"Attempting to send answer to {producer_url}, attempt {attempt + 1}")
                        producer_answer_response = await client.post(
                            producer_url,
                            headers={"accept": "application/json", "Content-Type": "application/json"},
                            json=answer_data
                        )
                        if producer_answer_response.status_code == 200:
                            logger.info(f"Answer sent to producer: {answer_data}")
                            break
                        else:
                            logger.warning(f"Failed to send answer to {producer_url}: {producer_answer_response.status_code}")
                    except httpx.RequestError as e:
                        logger.error(f"Connection error to {producer_url}: {str(e)}")
                        if attempt == 2:
                            logger.error(f"All retries failed for {producer_url}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                if not producer_answer_response or producer_answer_response.status_code != 200:
                    await websocket.send_json({"error": "Failed to send answer to producer after all retries"})
                    continue

                # Step 6: Fetch answer from consumer_service
                consumer_answer_response = None
                for attempt in range(3):  # Retry 3 times
                    try:
                        logger.info(f"Attempting to fetch answer from {consumer_url}, attempt {attempt + 1}")
                        consumer_answer_response = await client.get(
                            consumer_url,
                            params={"topic": "answer", "limit": 1, "latest": True}
                        )
                        if consumer_answer_response.status_code == 200:
                            break
                        else:
                            logger.warning(f"Failed to fetch answer from {consumer_url}: {consumer_answer_response.status_code}")
                    except httpx.RequestError as e:
                        logger.error(f"Connection error to {consumer_url}: {str(e)}")
                        if attempt == 2:
                            logger.error(f"All retries failed for {consumer_url}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                if not consumer_answer_response or consumer_answer_response.status_code != 200:
                    await websocket.send_json({"error": "Failed to fetch answer from consumer"})
                    continue
                consumer_answer_data = consumer_answer_response.json()
                if consumer_answer_data["count"] == 0 or consumer_answer_data["messages"][0]["value"]["message_id"] != message_id:
                    await websocket.send_json({"error": "Answer not found in consumer"})
                    continue
                logger.info(f"Answer fetched from consumer: {consumer_answer_data}")

                # Step 7: Send response back to WebSocket client
                await websocket.send_json({
                    "session_id": session_id,
                    "query": query,
                    "response": response
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
        await websocket.send_json({"error": f"Internal error: {str(e)}"})
    finally:
        async with connection_lock:
            active_connections.pop(session_id, None)
            await session_manager.delete_session(session_id)

# Session history API
@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    history = session["conversation_history"] + chat_histories[session_id]
    return {"session_id": session_id, "conversation_history": history}

# Delete session endpoint
@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await session_manager.delete_session(session_id)
    return {"status": "success", "message": f"Session {session_id} deleted"}

@app.get("/api/images")
async def list_images():
    """Return a list of available images"""
    images_dir = "ingestion/components/images"
    if not os.path.exists(images_dir):
        return {"images": []}
    
    image_files = []
    for filename in os.listdir(images_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg')):
            image_files.append({
                "name": filename,
                "url": f"/images/{filename}"
            })
    
    return {"images": image_files}

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