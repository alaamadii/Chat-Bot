from intake.models import NormalizedMessage
from ai_brain.models import FinalOutput

class HumanHandoff:
    """
    Task 10: Human Handoff
    Escalate to live agent smoothly
    """
    def escalate(self, message: NormalizedMessage, ai_output: FinalOutput) -> str:
        # Simulate sending a webhook to a dashboard like Zendesk
        print(f"[Human Handoff] Alerting Agent Dashboard for Session {message.session_id}!")
        print(f"[Human Handoff] Reason: Confidence too low ({ai_output.confidence_score}) or Intent requires human.")
        
        # Return fallback message for the user
        return "I have transferred your chat to a customer service representative. Please hold on for a moment."

handoff = HumanHandoff()
