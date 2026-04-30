from ai_brain.models import AIResponse, Intent, FinalOutput

class ConfidenceScorer:
    """
    Task 7: Confidence Scorer
    Rate answer quality & escalate
    """
    def score(self, response: AIResponse, intent: Intent) -> FinalOutput:
        # Base score on intent confidence
        score = intent.confidence
        
        # Artificial penalty if intent is support/complaint, as they usually need human touch
        if intent.category == "support":
            score -= 0.3
            
        escalate = score < 0.6
        
        return FinalOutput(
            response=response,
            confidence_score=score,
            escalate_to_human=escalate
        )

scorer = ConfidenceScorer()
