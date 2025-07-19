from pydantic import BaseModel
from typing import Optional

class BaseMessage(BaseModel):
    event_id: str
    timestamp: float
    version: str = "1.0"

class OrderMessage(BaseMessage):
    order_id: str
    user_id: str
    items: list[dict]
    metadata: Optional[dict] = None