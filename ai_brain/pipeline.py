from ai_brain.intent_classifier import classifier
from ai_brain.context_builder import context_builder
from ai_brain.response_generator import generator
from ai_brain.confidence_scorer import scorer
from ai_brain.models import FinalOutput
from intake.models import NormalizedMessage
from typing import List

def process_message(message: NormalizedMessage, history: List[NormalizedMessage]) -> FinalOutput:
    """
    Orchestrates the AI Brain Pipeline (Tasks 4-7)
    """
    # Convert history models to dicts for the context builder
    history_dicts = [msg.model_dump() for msg in history]
    
    # Task 4: Intent Classification
    intent = classifier.classify(message.clean_text)
    
    # Task 5: Context Building
    context = context_builder.build_context(intent, history_dicts)
    
    # Task 6: Response Generation
    ai_response = generator.generate(message.clean_text, intent, context)
    
    # Task 7: Confidence Scoring
    final_output = scorer.score(ai_response, intent)
    
    return final_output
