from fastapi import FastAPI, HTTPException
from intake.models import IncomingMessage, NormalizedMessage
from intake.normalizer import normalize_message
from intake.session_manager import session_manager
from typing import List

app = FastAPI(title="Chatbot Intake Service")

@app.post("/webhook/whatsapp", response_model=NormalizedMessage)
async def whatsapp_webhook(payload: dict):
    """
    Simulates a webhook endpoint for WhatsApp.
    Normally, you would parse the specific WhatsApp provider format (e.g., Twilio or Meta Graph API).
    Here we expect a simplified dictionary for demonstration.
    """
    try:
        # For demo purposes, we map a generic payload structure to our model
        msg = IncomingMessage(
            channel="whatsapp",
            user_id=payload.get("From", "unknown_user"),
            text=payload.get("Body", ""),
            metadata={"raw_payload": payload}
        )
        
        # 1. Get or create session
        session_id = session_manager.get_or_create_session(msg.user_id)
        
        # 2. Normalize message
        normalized = normalize_message(msg, session_id=session_id)
        
        # 3. Store in session
        session_manager.add_message(normalized)
        
        return normalized

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/webhook/web", response_model=NormalizedMessage)
async def web_webhook(msg: IncomingMessage):
    """
    Webhook endpoint for the Web Chat channel.
    Expects the payload to already match the IncomingMessage format.
    """
    # Force channel to be web
    msg.channel = "web_chat"
    
    # 1. Get or create session
    session_id = session_manager.get_or_create_session(msg.user_id)
    
    # 2. Normalize message
    normalized = normalize_message(msg, session_id=session_id)
    
    # 3. Store in session
    session_manager.add_message(normalized)
    
    return normalized

@app.get("/session/{session_id}/history", response_model=List[NormalizedMessage])
async def get_session_history(session_id: str):
    """
    Endpoint to retrieve the conversation history for a given session.
    """
    history = session_manager.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty")
    return history

@app.get("/health")
async def health_check():
    return {"status": "ok"}
