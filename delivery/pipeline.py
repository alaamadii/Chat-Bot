from actions.models import ExecutionResult
from delivery.models import DeliveryStatus
from delivery.formatter import formatter
from delivery.safety import safety_filter
from delivery.engine import engine


def deliver_response(
    execution_result: ExecutionResult,
    channel: str,
    user_id: str,
    send_network: bool = True,
) -> DeliveryStatus:
    """Format, safety-check and deliver the final response."""
    formatted_msg = formatter.format(execution_result.message_to_user, channel)
    safe_msg = safety_filter.check(formatted_msg)
    return engine.send(safe_msg, channel, user_id, send_network=send_network)
