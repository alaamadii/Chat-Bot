import os
import time

from dotenv import load_dotenv

from ai_brain.models import AIResponse, Context, Intent
from ai_brain.providers import get_llm_provider

load_dotenv()


class ResponseGenerator:
    """Generate grounded responses through a configurable provider abstraction."""

    def __init__(self):
        self.temperature = float(os.getenv("AI_TEMPERATURE", "0.3"))

    def generate(self, user_message: str, intent: Intent, context: Context) -> AIResponse:
        try:
            provider = get_llm_provider()
        except Exception as exc:
            return AIResponse(
                text="Sorry, I am having trouble connecting to the AI service. Please try again later.",
                reasoning=f"Provider init error: {type(exc).__name__}",
                provider="unavailable",
                model="unavailable",
            )

        system_instruction = f"""
You are a helpful customer service assistant for NextTech, a software and AI solutions company in Dubai.
The user's structured intent is: {intent.category}.

Relevant knowledge base snippets:
{chr(10).join(context.knowledge_snippets)}

Rules:
1. Answer politely in English.
2. Only use the provided knowledge snippets for factual company information.
3. If the answer is not available, clearly say so rather than inventing it.
4. Be concise and professional.
"""
        started = time.perf_counter()
        try:
            result = provider.generate(
                prompt=f"User Message: {user_message}",
                system_instruction=system_instruction,
                temperature=self.temperature,
            )
            reply = result.text
            input_tokens = result.input_tokens
            output_tokens = result.output_tokens
            note = f"Grounded on {len(context.knowledge_snippets)} knowledge snippets"
        except Exception as exc:
            reply = "An unexpected error occurred while processing your request."
            input_tokens = 0
            output_tokens = 0
            note = f"Generation error: {type(exc).__name__}"

        latency_ms = int((time.perf_counter() - started) * 1000)
        return AIResponse(
            text=reply.strip(),
            reasoning=note,
            provider=provider.name,
            model=provider.model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


generator = ResponseGenerator()
