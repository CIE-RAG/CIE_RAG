#Consumer API 
#Will call the Kafka Library - Consumer Client to get the latest messages or the Last N messages
#specified by the parameter

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from kafka_lib.consumer import KafkaConsumerClient
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("consumer-service")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and clean up Kafka consumer"""
    consumer = KafkaConsumerClient(
        topic="messages",
        group_id="message-fetcher"
    )
    app.state.consumer = consumer
    logger.info("Kafka consumer initialized")
    
    yield
    
    consumer.close()
    logger.info("Kafka consumer closed")

app = FastAPI(lifespan=lifespan)

@app.get("/messages")
async def get_messages(topic: str, limit: int = 10, latest: bool = False):
    """
    Fetch messages from Kafka
    Parameters:
    - limit: Maximum number of messages to return (default: 10)
    - latest: If True, returns only new messages since last call (default: False)
    """
    try:
        consumer = KafkaConsumerClient(
            topic=topic,
            group_id=f"{topic}-fetcher"
        )

        if latest:
            # ✅ Use the new get_next_message method
            msg = await consumer.get_next_message()
            return JSONResponse({
                "status": "success",
                "count": 1,
                "messages": [msg]
            })
        else:
            # 🟩 Existing logic preserved
            messages = consumer.get_all_messages(limit=limit)
            return JSONResponse({
                "status": "success",
                "count": len(messages),
                "messages": messages
            })

    except Exception as e:
        logger.error(f"Failed to fetch messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Consumer service is running"}

@app.get("/health")
async def health():
    try:
        test_msgs = app.state.consumer.get_all_messages(limit=1)
        return {
            "status": "healthy",
            "kafka_connected": True,
            "message_count": len(test_msgs)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "kafka_connected": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
