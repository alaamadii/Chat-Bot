from ai_brain.models import FinalOutput
from intake.models import NormalizedMessage
from actions.models import ExecutionResult
from actions.integrator import integrator
from actions.handoff import handoff

class ActionRouter:
    """
    Task 8: Action Router
    Decide: reply / API call / ticket
    """
    def route(self, message: NormalizedMessage, ai_output: FinalOutput) -> ExecutionResult:
        # 1. Check for escalation
        if ai_output.escalate_to_human:
            fallback_msg = handoff.escalate(message, ai_output)
            return ExecutionResult(
                status="handoff",
                action_taken="sent_to_agent",
                message_to_user=fallback_msg
            )
            
        # 2. Check for API actions based on intent
        if ai_output.response.reasoning and "pricing" in ai_output.response.reasoning:
            # Maybe the intent was pricing/sales, let's log a lead
            ticket_id = integrator.create_crm_lead(message)
            return ExecutionResult(
                status="success",
                action_taken="ticket_created",
                message_to_user=ai_output.response.text,
                internal_data={"lead_id": ticket_id}
            )
            
        # 3. Default: Just reply
        return ExecutionResult(
            status="success",
            action_taken="reply_only",
            message_to_user=ai_output.response.text
        )

router = ActionRouter()
