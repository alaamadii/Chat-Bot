from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class IncomingMessage(BaseModel):
    """
    Generic model for an incoming message payload from any channel.
    """
    channel: str = Field(..., description="e.g., whatsapp, web_chat, email")
    user_id: str = Field(..., description="Unique identifier for the user (e.g., phone number, email, session id)")
    text: str = Field(..., description="The raw message text")
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific metadata")

class NormalizedMessage(BaseModel):
    """
    The unified message format used internally by the AI engine.
    """
    session_id: str
    user_id: str
    channel: str
    original_text: str
    clean_text: str
    received_at: datetime
    metadata: Dict[str, Any]
