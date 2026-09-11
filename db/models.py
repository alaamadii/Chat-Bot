import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class ConversationStatus(str, enum.Enum):
    BOT_ACTIVE = "BOT_ACTIVE"
    WAITING_FOR_AGENT = "WAITING_FOR_AGENT"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.BOT_ACTIVE, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[str] = mapped_column(String(255))
    channel: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class ConversationAssignment(Base):
    __tablename__ = "conversation_assignments"
    __table_args__ = (UniqueConstraint("conversation_id", name="uq_assignment_conversation"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    agent_username: Mapped[str] = mapped_column(String(255), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)
    created_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
