from pydantic import BaseModel, Field
from typing import Optional

class InteractionLog(BaseModel):
    session_id: str
    user_id: str
    intent_category: str
    ai_confidence: float
    action_taken: str
    delivery_success: bool
    timestamp: str

class DashboardReport(BaseModel):
    total_interactions: int
    handoff_rate: float
    average_confidence: float
