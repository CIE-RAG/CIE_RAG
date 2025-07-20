# producer_service/main.py
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from kafka_lib.producer import KafkaProducerClient
from kafka_lib.schemas import OrderMessage
import os
import time
import random
import logging
from pydantic import BaseModel

from kafka_lib.admin import KafkaAdmin

admin = KafkaAdmin()
admin.create_topic("query")
admin.create_topic("prompt")
admin.create_topic("answer")


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("producer.api")

class Message(BaseModel):
    session_id: str
    user_id: str
    message_id: str
    type: str  
    message: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup delay if needed
    if os.getenv("STARTUP_DELAY"):
        delay = int(os.getenv("STARTUP_DELAY"))
        logger.info(f"Waiting {delay} seconds before starting...")
        time.sleep(delay)
    
    # Initialize producer with retries
    max_retries = 3
    logger.debug("Initialize Producer and use 3 Retries")
    for attempt in range(max_retries):
        try:
            app.state.producer = KafkaProducerClient()
            logger.info("✅ Kafka producer connected")
            break
        except Exception as e:
            logger.error(f"❌ Producer connection attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to initialize producer after {max_retries} attempts")
            wait = 2 ** (attempt + 1)
            logger.debug(f"⚠️ Retry {attempt + 1}/{max_retries}: Waiting {wait}s...")
            time.sleep(wait)
    
    yield  # App runs here
    
    # Cleanup
    logger.info("🛑 Closing producer...")
    app.state.producer.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Producer service is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/send_message")
async def send_message(request: Request, msg: Message):
    logger.debug(f"Incoming Request: {request.query_params}")
    """Endpoint that produces messages to Kafka"""
    try:
        k = random.randint(1, 999)
        logger.info(f"Sending Message to Kafka: {msg.message}, key: {k}")
        
        app.state.producer.send(
        topic=msg.type,  # Use type as topic
        key=msg.message_id,
        message=msg.dict()  # Send full message
        )
        
        # Flush to ensure message is sent
        app.state.producer.flush()
        
        logger.info(f"Message queued (ID: {k})")
        return {"status": "queued", "message_id": str(k)}
    
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)