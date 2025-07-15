# Integrated FastAPI application combining WebSocket session management with Redis and UI endpoints
# pip install fastapi uvicorn redis httpx python-jose[cryptography] passlib
#By:Tanmaya K 10/10/25

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

# Set up logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None

# WebSocket timeout configuration (5 minutes)
WEBSOCKET_TIMEOUT = float(os.getenv("WEBSOCKET_TIMEOUT", "300"))

# Session expiration time (24 hours)
SESSION_EXPIRY = int(os.getenv("SESSION_EXPIRY", "86400"))

# JSON file for storing conversation history
CHAT_HISTORY_FILE = "chat_history.json"

# In-memory store for active WebSocket connections
active_connections = {}

# In-memory store for user and query data (from UI_WebSocket.py)
stored_users = []
stored_queries = []

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Pydantic models for user and query data
class User(BaseModel):
    name: str
    email: str

class Message(BaseModel):
    text: str

# Simulated user authentication dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token  # Return user_id

# Session Manager class to handle session lifecycle and conversation history
class SessionManager:
    def __init__(self):
        # Ensure chat history JSON file exists
        if not os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'w') as f:
                json.dump({}, f)

    async def create_session(self, user_id: str, websocket: WebSocket = None):
        session_id = f"{user_id}_{str(uuid.uuid4())}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "conversation_history": [],
            "created_at": datetime.now().isoformat()
        }
        
        # Store session data in Redis with expiration
        await redis_client.hset(
            f"session:{session_id}", 
            mapping={
                "data": json.dumps(session_data),
                "user_id": user_id,
                "created_at": session_data["created_at"]
            }
        )
        await redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
        
        # Store user session mapping for quick lookup
        await redis_client.set(f"user_session:{user_id}", session_id, ex=SESSION_EXPIRY)
        
        if websocket:
            active_connections[session_id] = websocket
        
        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session_id

    async def get_session(self, session_id: str):
        session_data = await redis_client.hget(f"session:{session_id}", "data")
        if session_data:
            return json.loads(session_data)
        return None

    async def get_or_create_session(self, user_id: str, websocket: WebSocket = None):
        # Check if user already has an active session
        existing_session_id = await redis_client.get(f"user_session:{user_id}")
        if existing_session_id:
            session_id = existing_session_id.decode('utf-8')
            # Verify session still exists
            session_exists = await redis_client.exists(f"session:{session_id}")
            if session_exists:
                if websocket:
                    active_connections[session_id] = websocket
                return session_id
        
        # Create new session if none exists or expired
        return await self.create_session(user_id, websocket)

    async def update_session(self, session_id: str, query: str, response: str):
        # Get current session data
        session_data = await redis_client.hget(f"session:{session_id}", "data")
        if not session_data:
            logger.error(f"Session {session_id} not found")
            return
        
        session_dict = json.loads(session_data)
        
        # Add new conversation entry
        conversation_entry = {
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        session_dict["conversation_history"].append(conversation_entry)
        
        # Update session in Redis
        await redis_client.hset(
            f"session:{session_id}", 
            "data", 
            json.dumps(session_dict)
        )
        
        # Refresh expiration
        await redis_client.expire(f"session:{session_id}", SESSION_EXPIRY)
        
        # Save to JSON file as backup
        await self.save_to_json(session_id, query, response)

    async def save_to_json(self, session_id: str, query: str, response: str):
        try:
            with open(CHAT_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except json.JSONDecodeError:
            history = {}
        
        if session_id not in history:
            history[session_id] = []
        
        history[session_id].append({
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)

    async def get_session_history(self, session_id: str):
        session_data = await self.get_session(session_id)
        if session_data:
            return session_data.get("conversation_history", [])
        return []

    async def delete_session(self, session_id: str):
        # Get user_id before deleting
        user_id = await redis_client.hget(f"session:{session_id}", "user_id")
        if user_id:
            user_id = user_id.decode('utf-8')
            await redis_client.delete(f"user_session:{user_id}")
        
        # Delete session data
        await redis_client.delete(f"session:{session_id}")
        
        # Remove from active connections
        if session_id in active_connections:
            del active_connections[session_id]
        
        logger.info(f"Deleted session: {session_id}")

    async def cleanup_sessions(self):
        while True:
            try:
                # Clean up disconnected WebSocket connections
                for session_id in list(active_connections.keys()):
                    websocket = active_connections[session_id]
                    if not hasattr(websocket, 'application_state') or not websocket.application_state.connected:
                        await self.delete_session(session_id)
                        logger.info(f"Cleaned up disconnected session: {session_id}")
                
                # Redis handles expiration automatically, but we can do additional cleanup here
                # Get all session keys and check for orphaned data
                session_keys = await redis_client.keys("session:*")
                for key in session_keys:
                    key_str = key.decode('utf-8')
                    ttl = await redis_client.ttl(key_str)
                    if ttl == -1:  # Key without expiration
                        await redis_client.expire(key_str, SESSION_EXPIRY)
                        logger.info(f"Added expiration to key: {key_str}")
                
            except Exception as e:
                logger.error(f"Error in session cleanup: {str(e)}")
            
            await asyncio.sleep(60)  # Run cleanup every minute

# Initialize session manager
session_manager = SessionManager()

# Initialize Redis connection
async def init_redis():
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise

# Health check endpoint
@app.get("/")
async def health():
    try:
        await redis_client.ping()
        return {"status": "FastAPI is running", "redis": "connected"}
    except Exception as e:
        return {"status": "FastAPI is running", "redis": "disconnected", "error": str(e)}

# Login endpoint to simulate user authentication
@app.post("/login")
async def login(username: str):
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    return {"token": username, "user_id": username}

# User endpoint to store user data
@app.post("/user")
def user(user: User):
    user_data = {"name": user.name, "email": user.email}
    stored_users.append(user_data)
    print(f"Received user: {user.name}, {user.email}")
    return {"user_name": user.name, "user_mail": user.email, "status": "success"}

# Get all users endpoint
@app.get("/user")
def get_users():
    return {"users": stored_users, "count": len(stored_users)}

# User query endpoint
@app.post("/user_query")
def post_user_query(message: Message):
    query_data = {"text": message.text, "timestamp": str(datetime.now())}
    stored_queries.append(query_data)
    print(f"Received query: {message.text}")
    return {"user_query": message.text, "response": f"Processed: {message.text}", "status": "success"}

# Get all queries endpoint
@app.get("/user_query")
def get_user_queries():
    return {"queries": stored_queries, "count": len(stored_queries)}

# HTTP endpoint to handle queries with session management
@app.post("/query")
async def handle_query(query_data: dict, user_id: str = Depends(get_current_user)):
    query = query_data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="No query provided")
    
    session_id = await session_manager.get_or_create_session(user_id)
    response = await get_llm_response(query)
    await session_manager.update_session(session_id, query, response)
    
    return {
        "session_id": session_id,
        "query": query,
        "response": response
    }

# Get session history endpoint
@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str, user_id: str = Depends(get_current_user)):
    session_data = await session_manager.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "session_id": session_id,
        "conversation_history": session_data.get("conversation_history", [])
    }

# WebSocket endpoint for real-time communication
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    session_id = None
    
    try:
        session_id = await session_manager.get_or_create_session(user_id, websocket)
        await websocket.send_json({"session_id": session_id})
        
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
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if session_id and session_id in active_connections:
            del active_connections[session_id]

# Placeholder function for LLM response (replace with your actual implementation)
async def get_llm_response(query: str) -> str:
    # Simulate processing time
    await asyncio.sleep(0.1)
    return f"Echo: {query}"

# Function to interact with existing FastAPI/Kafka pipeline
# async def get_llm_response(query: str) -> str:
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.post(
#                 "http://your-fastapi-backend:port/process_query",
#                 json={"query": query}
#             )
#             response.raise_for_status()
#             return response.json().get("response", "Error: No response from backend")
#         except Exception as e:
#             logger.error(f"Error calling FastAPI backend: {str(e)}")
#             return "Error: Failed to process query"

async def stream_llm_response(query: str, websocket: WebSocket, session_id: str):
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", "http://your-llm-service/stream", json={"query": query}) as response:
                async for chunk in response.aiter_text():
                    await websocket.send_json({
                        "session_id": session_id,
                        "chunk": chunk,
                        "type": "stream"
                    })
    except Exception as e:
        logger.error(f"Error calling FastAPI backend: {str(e)}")
        await websocket.send_json({"error": "Failed to process query"})

# Startup event to initialize Redis and session cleanup
@app.on_event("startup")
async def startup_event():
    await init_redis()
    asyncio.create_task(session_manager.cleanup_sessions())

# Shutdown event to close Redis connection
@app.on_event("shutdown")
async def shutdown_event():
    if redis_client:
        await redis_client.close()

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)