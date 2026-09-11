from ai_brain.models import AIResponse, FinalOutput, Intent


class ConfidenceScorer:
    """Combine intent confidence with simple escalation policy."""

    def score(self, response: AIResponse, intent: Intent) -> FinalOutput:
        score = intent.confidence
        if intent.category == "support":
            score -= 0.3
        score = max(0.0, min(1.0, score))
        return FinalOutput(
            response=response,
            intent=intent,
            confidence_score=score,
            escalate_to_human=score < 0.6,
        )


scorer = ConfidenceScorer()
