from actions.models import ExecutionResult
from delivery.engine import engine
from delivery.formatter import formatter
from delivery.models import DeliveryStatus
from delivery.safety import safety_filter
from services.outbox import outbox


def deliver_response(
    execution_result: ExecutionResult,
    channel: str,
    user_id: str,
    send_network: bool = True,
) -> DeliveryStatus:
    """Format, safety-check and deliver the final response.

    WhatsApp network sends are persisted to the outbox before delivery so a
    failed request can be recovered by the standalone outbox worker.
    """
    formatted_msg = formatter.format(execution_result.message_to_user, channel)
    safe_msg = safety_filter.check(formatted_msg)

    if channel == "whatsapp" and send_network:
        item = outbox.enqueue(channel=channel, recipient=user_id, text=safe_msg.text)
        return outbox.deliver_now(item.id)

    return engine.send(safe_msg, channel, user_id, send_network=send_network)
