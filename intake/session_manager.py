from typing import List

from db.models import ConversationStatus
from db.repository import conversation_repository
from intake.models import NormalizedMessage


class SessionManager:
    """Database-backed conversation/session facade kept for backwards compatibility."""

    def get_or_create_session(self, user_id: str, channel: str = "web_chat") -> str:
        conversation = conversation_repository.get_or_create_conversation(user_id, channel)
        return conversation.id

    def add_message(self, message: NormalizedMessage, role: str = "user") -> None:
        conversation_repository.add_message(message, role=role)

    def add_assistant_message(self, session_id: str, user_id: str, channel: str, text: str) -> None:
        conversation_repository.add_text_message(
            conversation_id=session_id,
            role="assistant",
            user_id=user_id,
            channel=channel,
            text=text,
        )

    def get_history(self, session_id: str) -> List[NormalizedMessage]:
        return conversation_repository.get_history(session_id)

    def set_status(self, session_id: str, status: ConversationStatus) -> None:
        conversation_repository.set_status(session_id, status)


session_manager = SessionManager()
