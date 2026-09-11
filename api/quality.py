from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.security import require_roles
from services.quality import create_feedback, quality_summary

router = APIRouter(tags=["quality"])


class FeedbackRequest(BaseModel):
    conversation_id: str
    user_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=4000)


@router.post("/feedback", status_code=201)
async def submit_feedback(payload: FeedbackRequest):
    try:
        return create_feedback(
            conversation_id=payload.conversation_id,
            user_id=payload.user_id,
            rating=payload.rating,
            comment=payload.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/admin/quality")
async def ai_quality(user: dict = Depends(require_roles("admin"))):
    return quality_summary()
