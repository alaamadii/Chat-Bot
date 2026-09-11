from typing import List

from ai_brain.confidence_scorer import scorer
from ai_brain.context_builder import context_builder
from ai_brain.intent_classifier import classifier
from ai_brain.models import FinalOutput
from ai_brain.response_generator import generator
from intake.models import NormalizedMessage


def process_message(message: NormalizedMessage, history: List[NormalizedMessage]) -> FinalOutput:
    """Run intent classification, RAG context retrieval, generation and scoring."""
    history_dicts = [msg.model_dump() for msg in history]
    intent = classifier.classify(message.clean_text)
    context = context_builder.build_context(intent, history_dicts, message.clean_text)
    ai_response = generator.generate(message.clean_text, intent, context)
    return scorer.score(ai_response, intent)
