from fastapi import FastAPI, Form, Query
import httpx

app = FastAPI()

# POST: Forward form to producer
@app.post("/send")
async def send_form(
    session_id: str = Form(...),
    user_id: str = Form(...),
    message_id: str = Form(...),
    type: str = Form(...),
    message: str = Form(...)
):
    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "message_id": message_id,
        "type": type,
        "message": message
    }

    async with httpx.AsyncClient() as client:
        response = await client.post("http://producer:8000/send_message", json=payload)

    return {
        "status": "Message forwarded",
        "producer_response": response.json()
    }

# ✅ GET: Fetch messages from consumer
@app.get("/messages")
async def get_messages(
    type: str = Query(..., description="query | prompt | answer"),
    limit: int = Query(10, description="Number of messages to fetch"),
    latest: bool = Query(False, description="Return the next unconsumed message if true")
):
    topic_map = {
        "query": "query",
        "prompt": "prompt",
        "answer": "answer"
    }

    if type not in topic_map:
        return {"error": f"Invalid type: {type}. Must be one of: query, prompt, answer"}

    topic = topic_map[type]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://consumer:8001/messages",
            params={
                "topic": topic,
                "limit": limit,
                "latest": latest
            }
        )

    return response.json()  # Only return the actual messages
