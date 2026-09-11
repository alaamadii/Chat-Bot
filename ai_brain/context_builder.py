from typing import Any, Dict, List

from ai_brain.models import Context, Intent
from knowledge.retriever import retriever


class ContextBuilder:
    """Builds conversational context using query-based knowledge retrieval."""

    def build_context(
        self,
        intent: Intent,
        history: List[Dict[str, Any]],
        user_message: str,
    ) -> Context:
        snippets = retriever.retrieve(user_message, top_k=4)
        return Context(
            user_history=history[-5:],
            knowledge_snippets=snippets,
        )


context_builder = ContextBuilder()
