from actions.models import ExecutionResult
from delivery.models import DeliveryStatus
from delivery.formatter import formatter
from delivery.safety import safety_filter
from delivery.engine import engine

def deliver_response(execution_result: ExecutionResult, channel: str, user_id: str) -> DeliveryStatus:
    """
    Orchestrates the Delivery & Quality layer (Tasks 11-13).
    """
    # Task 11: Format the message for the specific channel
    formatted_msg = formatter.format(execution_result.message_to_user, channel)
    
    # Task 12: Run safety checks
    safe_msg = safety_filter.check(formatted_msg)
    
    # Task 13: Deliver to channel
    status = engine.send(safe_msg, channel, user_id)
    
    return status
