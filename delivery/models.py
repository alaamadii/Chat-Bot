from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class FormattedMessage(BaseModel):
    text: str = Field(..., description="The final polished string to be sent")
    media_urls: Optional[list[str]] = Field(default_factory=list, description="URLs to any attachments")
    is_safe: bool = Field(default=True, description="Flagged if safety filter caught something")

class DeliveryStatus(BaseModel):
    success: bool
    channel: str
    timestamp: str
    error_details: Optional[str] = None
