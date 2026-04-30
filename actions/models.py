from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ExecutionResult(BaseModel):
    status: str = Field(..., description="e.g., success, handoff, api_error")
    action_taken: str = Field(..., description="e.g., reply_only, ticket_created, sent_to_agent")
    message_to_user: str = Field(..., description="The final text sent to the user")
    internal_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Data like ticket ID or Agent assigned")
