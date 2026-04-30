import json
import os
from ai_brain.models import Context, Intent
from typing import List, Dict, Any

class ContextBuilder:
    """
    Task 5: Context Builder
    Load company KB & user data
    """
    def __init__(self, kb_path: str = "knowledge_base.json"):
        self.kb_path = kb_path
        self._kb_data = {}
        self._load_kb()

    def _load_kb(self):
        if os.path.exists(self.kb_path):
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                self._kb_data = json.load(f)

    def build_context(self, intent: Intent, history: List[Dict[str, Any]]) -> Context:
        snippets = []
        
        # Always include basic company info
        if "company_info" in self._kb_data:
            info = self._kb_data["company_info"]
            snippets.append(f"Company: {info.get('name')}, Hours: {info.get('working_hours', {}).get('time')}")

        # Add specific info based on intent (Mocking RAG retrieval)
        if intent.category == "pricing" and "services" in self._kb_data:
            services = [f"{s['name']}: {s['price_start']} {s['currency']}" for s in self._kb_data["services"]]
            snippets.append("Pricing: " + ", ".join(services))
            
        elif intent.category == "faq" and "faqs" in self._kb_data:
            faqs = [f"Q: {f['question']} A: {f['answer']}" for f in self._kb_data["faqs"]]
            snippets.extend(faqs)

        return Context(
            user_history=history[-5:], # Keep last 5 messages for context
            knowledge_snippets=snippets
        )

context_builder = ContextBuilder()
