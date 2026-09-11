from typing import Optional

from sqlalchemy import select

from db.database import SessionLocal
from db.models import Conversation, ConversationStatus, Message
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

    def set_status(self, conversation_id: str, status: ConversationStatus) -> None:
        with SessionLocal() as db:
            conversation = db.get(Conversation, conversation_id)
            if conversation:
                conversation.status = status
                db.commit()

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


conversation_repository = ConversationRepository()
