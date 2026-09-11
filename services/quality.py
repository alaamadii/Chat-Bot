from sqlalchemy import func, select

from db.database import SessionLocal
from db.models import AIInteractionMetric, Conversation, ConversationFeedback


def record_ai_metric(conversation_id: str, ai_output) -> None:
    with SessionLocal() as db:
        db.add(
            AIInteractionMetric(
                conversation_id=conversation_id,
                intent=ai_output.intent.category,
                confidence=ai_output.confidence_score,
                provider=ai_output.response.provider,
                model=ai_output.response.model,
                latency_ms=ai_output.response.latency_ms,
                escalated=ai_output.escalate_to_human,
            )
        )
        db.commit()


def create_feedback(conversation_id: str, user_id: str, rating: int, comment: str | None = None) -> dict:
    with SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)
        if not conversation or conversation.user_id != user_id:
            raise ValueError("Conversation not found")
        item = ConversationFeedback(
            conversation_id=conversation_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"id": item.id, "conversation_id": item.conversation_id, "rating": item.rating}


def quality_summary() -> dict:
    with SessionLocal() as db:
        total = db.scalar(select(func.count()).select_from(AIInteractionMetric)) or 0
        avg_latency = db.scalar(select(func.avg(AIInteractionMetric.latency_ms))) or 0
        avg_confidence = db.scalar(select(func.avg(AIInteractionMetric.confidence))) or 0
        escalations = db.scalar(select(func.count()).select_from(AIInteractionMetric).where(AIInteractionMetric.escalated.is_(True))) or 0
        feedback_count = db.scalar(select(func.count()).select_from(ConversationFeedback)) or 0
        avg_rating = db.scalar(select(func.avg(ConversationFeedback.rating))) or 0
        return {
            "ai_interactions": total,
            "avg_latency_ms": round(float(avg_latency), 2),
            "avg_confidence": round(float(avg_confidence), 3),
            "escalation_rate": round(escalations / total, 3) if total else 0.0,
            "feedback_count": feedback_count,
            "avg_rating": round(float(avg_rating), 2),
        }
