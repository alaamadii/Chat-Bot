from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Intent(BaseModel):
    category: str = Field(..., description="e.g., faq, pricing, support, general")
    confidence: float = Field(..., description="Confidence score of the classification (0-1)")

class Context(BaseModel):
    user_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent messages")
    knowledge_snippets: List[str] = Field(default_factory=list, description="RAG retrieved info")

class AIResponse(BaseModel):
    text: str = Field(..., description="The generated reply")
    reasoning: str = Field(..., description="Internal thought process for the reply")

class FinalOutput(BaseModel):
    response: AIResponse
    confidence_score: float = Field(..., description="Final confidence in the answer (0-1)")
    escalate_to_human: bool = Field(default=False, description="True if confidence is too low or user requested human")
