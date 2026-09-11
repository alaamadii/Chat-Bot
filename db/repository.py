from typing import Optional

from sqlalchemy import func, select

from db.database import SessionLocal
from db.models import (
    Conversation,
    ConversationAssignment,
    ConversationStatus,
    KnowledgeEntry,
    Message,
)
from intake.models import NormalizedMessage


ACTIVE_STATUSES = {
    ConversationStatus.BOT_ACTIVE,
    ConversationStatus.WAITING_FOR_AGENT,
    ConversationStatus.HUMAN_ACTIVE,
}


class ConversationRepository:
    def get_or_create_conversation(self, user_id: str, channel: str) -> Conversation:
        with SessionLocal() as db:
            stmt = (
                select(Conversation)
                .where(
                    Conversation.user_id == user_id,
                    Conversation.channel == channel,
                    Conversation.status.in_(ACTIVE_STATUSES),
                )
                .order_by(Conversation.created_at.desc())
            )
            conversation = db.scalars(stmt).first()
            if conversation:
                db.expunge(conversation)
                return conversation

            conversation = Conversation(user_id=user_id, channel=channel)
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            db.expunge(conversation)
            return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        with SessionLocal() as db:
            conversation = db.get(Conversation, conversation_id)
            if conversation:
                db.expunge(conversation)
            return conversation

    def list_conversations(self, limit: int = 100) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(Conversation).order_by(Conversation.updated_at.desc()).limit(limit)
            rows = list(db.scalars(stmt).all())
            assignment_rows = list(db.scalars(select(ConversationAssignment)).all())
            assignments = {a.conversation_id: a.agent_username for a in assignment_rows}
            return [
                {
                    "id": c.id,
                    "user_id": c.user_id,
                    "channel": c.channel,
                    "status": c.status.value,
                    "assigned_agent": assignments.get(c.id),
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in rows
            ]

    def list_messages(self, conversation_id: str) -> list[dict]:
        with SessionLocal() as db:
            stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
            rows = list(db.scalars(stmt).all())
            return [
                {
                    "id": m.id,
                    "role": m.role,
                    "user_id": m.user_id,
                    "channel": m.channel,
                    "text": m.text,
                    "metadata": m.metadata_json or {},
                    "created_at": m.created_at.isoformat(),
                }
                for m in rows
            ]

    def set_status(self, conversation_id: str, status: ConversationStatus) -> None:
        with SessionLocal() as db:
            conversation = db.get(Conversation, conversation_id)
            if conversation:
                conversation.status = status
                db.commit()

    def assign_agent(self, conversation_id: str, agent_username: str) -> dict:
        with SessionLocal() as db:
            conversation = db.get(Conversation, conversation_id)
            if not conversation:
                raise ValueError("Conversation not found")
            assignment = db.scalar(
                select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation_id)
            )
            if assignment:
                assignment.agent_username = agent_username
            else:
                assignment = ConversationAssignment(
                    conversation_id=conversation_id,
                    agent_username=agent_username,
                )
                db.add(assignment)
            conversation.status = ConversationStatus.HUMAN_ACTIVE
            db.commit()
            db.refresh(assignment)
            return {
                "conversation_id": conversation_id,
                "agent_username": assignment.agent_username,
                "status": conversation.status.value,
            }

    def get_assignment(self, conversation_id: str) -> Optional[str]:
        with SessionLocal() as db:
            assignment = db.scalar(
                select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation_id)
            )
            return assignment.agent_username if assignment else None

    def add_message(self, message: NormalizedMessage, role: str = "user") -> None:
        self.add_text_message(
            conversation_id=message.session_id,
            role=role,
            user_id=message.user_id,
            channel=message.channel,
            text=message.clean_text,
            metadata=message.metadata,
        )

    def add_text_message(
        self,
        conversation_id: str,
        role: str,
        user_id: str,
        channel: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        with SessionLocal() as db:
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role=role,
                    user_id=user_id,
                    channel=channel,
                    text=text,
                    metadata_json=metadata or {},
                )
            )
            conversation = db.get(Conversation, conversation_id)
            if conversation:
                conversation.updated_at = func.now()
            db.commit()

    def get_history(self, conversation_id: str) -> list[NormalizedMessage]:
        with SessionLocal() as db:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id, Message.role == "user")
                .order_by(Message.created_at.asc())
            )
            messages = list(db.scalars(stmt).all())
            return [
                NormalizedMessage(
                    session_id=item.conversation_id,
                    user_id=item.user_id,
                    channel=item.channel,
                    original_text=item.text,
                    clean_text=item.text,
                    received_at=item.created_at,
                    metadata=item.metadata_json or {},
                )
                for item in messages
            ]

    def analytics_summary(self) -> dict:
        with SessionLocal() as db:
            total = db.scalar(select(func.count()).select_from(Conversation)) or 0
            messages = db.scalar(select(func.count()).select_from(Message)) or 0
            waiting = db.scalar(
                select(func.count()).select_from(Conversation).where(
                    Conversation.status == ConversationStatus.WAITING_FOR_AGENT
                )
            ) or 0
            human_active = db.scalar(
                select(func.count()).select_from(Conversation).where(
                    Conversation.status == ConversationStatus.HUMAN_ACTIVE
                )
            ) or 0
            resolved = db.scalar(
                select(func.count()).select_from(Conversation).where(
                    Conversation.status == ConversationStatus.RESOLVED
                )
            ) or 0
            assigned = db.scalar(select(func.count()).select_from(ConversationAssignment)) or 0
            return {
                "total_conversations": total,
                "total_messages": messages,
                "waiting_for_agent": waiting,
                "human_active": human_active,
                "resolved": resolved,
                "assigned_conversations": assigned,
            }


class KnowledgeRepository:
    def list_entries(self) -> list[dict]:
        with SessionLocal() as db:
            rows = list(db.scalars(select(KnowledgeEntry).order_by(KnowledgeEntry.updated_at.desc())).all())
            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "content": row.content,
                    "category": row.category,
                    "created_by": row.created_by,
                    "created_at": row.created_at.isoformat(),
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in rows
            ]

    def create_entry(self, title: str, content: str, category: str, created_by: str) -> dict:
        with SessionLocal() as db:
            row = KnowledgeEntry(
                title=title.strip(),
                content=content.strip(),
                category=category.strip() or "general",
                created_by=created_by,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return {
                "id": row.id,
                "title": row.title,
                "content": row.content,
                "category": row.category,
                "created_by": row.created_by,
            }

    def delete_entry(self, entry_id: str) -> bool:
        with SessionLocal() as db:
            row = db.get(KnowledgeEntry, entry_id)
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True

    def retrieval_chunks(self) -> list[str]:
        with SessionLocal() as db:
            rows = list(db.scalars(select(KnowledgeEntry)).all())
            return [f"{row.category}: {row.title}\n{row.content}" for row in rows]


conversation_repository = ConversationRepository()
knowledge_repository = KnowledgeRepository()
