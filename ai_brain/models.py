from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Intent(BaseModel):
    category: str = Field(..., description="e.g., faq, pricing, support, general")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score of the classification")


class Context(BaseModel):
    user_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent messages")
    knowledge_snippets: List[str] = Field(default_factory=list, description="RAG retrieved info")


class AIResponse(BaseModel):
    text: str = Field(..., description="The generated reply")
    reasoning: str = Field(default="", description="Operational generation note; never used for action routing")
    provider: str = Field(default="unknown")
    model: str = Field(default="unknown")
    latency_ms: int = Field(default=0, ge=0)


class FinalOutput(BaseModel):
    response: AIResponse
    intent: Intent
    confidence_score: float = Field(..., ge=0, le=1, description="Final confidence in the answer")
    escalate_to_human: bool = Field(default=False)
