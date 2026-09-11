import logging
from dataclasses import dataclass

from actions.pipeline import execute_action
from ai_brain.pipeline import process_message
from analytics.pipeline import record_interaction
from db.models import ConversationStatus
from db.repository import conversation_repository
from delivery.engine import engine as delivery_engine
from delivery.models import FormattedMessage
from delivery.pipeline import deliver_response
from intake.models import IncomingMessage, NormalizedMessage
from intake.normalizer import normalize_message
from intake.session_manager import session_manager

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    message: NormalizedMessage
    reply: str
    action_taken: str
    delivery_success: bool
    conversation_status: str


class ChatService:
    def process(self, incoming: IncomingMessage, deliver: bool = True) -> ChatResult:
        session_id = session_manager.get_or_create_session(incoming.user_id, incoming.channel)
        conversation = conversation_repository.get_conversation(session_id)
        history = session_manager.get_history(session_id)
        message = normalize_message(incoming, session_id=session_id)
        session_manager.add_message(message)

        if conversation and conversation.status in {
            ConversationStatus.WAITING_FOR_AGENT,
            ConversationStatus.HUMAN_ACTIVE,
        }:
            reply = "Your message has been added to the support conversation. A human agent will respond here."
            delivery = delivery_engine.send(
                FormattedMessage(text=reply),
                incoming.channel,
                incoming.user_id,
                send_network=deliver and incoming.channel == "whatsapp",
            )
            logger.info(
                "message routed to human support",
                extra={
                    "conversation_id": session_id,
                    "channel": incoming.channel,
                    "event": "message_routed_to_agent",
                },
            )
            return ChatResult(
                message=message,
                reply=reply,
                action_taken="routed_to_agent",
                delivery_success=delivery.success,
                conversation_status=conversation.status.value,
            )

        ai_output = process_message(message, history=history)
        execution_result = execute_action(message, ai_output)

        if execution_result.status == "handoff":
            status = ConversationStatus.WAITING_FOR_AGENT
            session_manager.set_status(session_id, status)
        else:
            status = ConversationStatus.BOT_ACTIVE

        delivery_status = deliver_response(
            execution_result, incoming.channel, incoming.user_id, send_network=deliver
        )

        session_manager.add_assistant_message(
            session_id=session_id,
            user_id=incoming.user_id,
            channel=incoming.channel,
            text=execution_result.message_to_user,
        )
        record_interaction(message, ai_output, execution_result, delivery_status)

        logger.info(
            "message processed",
            extra={
                "conversation_id": session_id,
                "channel": incoming.channel,
                "event": "message_processed",
            },
        )

        return ChatResult(
            message=message,
            reply=execution_result.message_to_user,
            action_taken=execution_result.action_taken,
            delivery_success=delivery_status.success,
            conversation_status=status.value,
        )


chat_service = ChatService()
