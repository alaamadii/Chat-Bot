import re
from datetime import datetime
from intake.models import IncomingMessage, NormalizedMessage
import uuid

def clean_text(text: str) -> str:
    """
    Sanitizes the text by removing excessive whitespace and basic unwanted characters.
    """
    if not text:
        return ""
    # Remove extra spaces and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_message(msg: IncomingMessage, session_id: str = None) -> NormalizedMessage:
    """
    Converts a raw IncomingMessage into a NormalizedMessage.
    """
    cleaned = clean_text(msg.text)
    
    # Parse timestamp or set current time
    received_at = datetime.utcnow()
    if msg.timestamp:
        try:
            # Try parsing basic ISO format, fallback to now if failed
            received_at = datetime.fromisoformat(msg.timestamp.replace('Z', '+00:00'))
        except ValueError:
            pass

    if not session_id:
        session_id = str(uuid.uuid4())

    return NormalizedMessage(
        session_id=session_id,
        user_id=msg.user_id,
        channel=msg.channel,
        original_text=msg.text,
        clean_text=cleaned,
        received_at=received_at,
        metadata=msg.metadata
    )
