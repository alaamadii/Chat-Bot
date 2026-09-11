from actions.handoff import handoff
from actions.integrator import integrator
from actions.models import ExecutionResult
from ai_brain.models import FinalOutput
from intake.models import NormalizedMessage


class ActionRouter:
    """Route deterministic business actions from structured AI output."""

    def route(self, message: NormalizedMessage, ai_output: FinalOutput) -> ExecutionResult:
        if ai_output.escalate_to_human:
            fallback_msg = handoff.escalate(message, ai_output)
            return ExecutionResult(
                status="handoff",
                action_taken="sent_to_agent",
                message_to_user=fallback_msg,
            )

        if ai_output.intent.category == "pricing":
            lead_id = integrator.create_crm_lead(message)
            return ExecutionResult(
                status="success",
                action_taken="crm_lead_created",
                message_to_user=ai_output.response.text,
                internal_data={"lead_id": lead_id, "intent": ai_output.intent.category},
            )

        return ExecutionResult(
            status="success",
            action_taken="reply_only",
            message_to_user=ai_output.response.text,
            internal_data={"intent": ai_output.intent.category},
        )


router = ActionRouter()
