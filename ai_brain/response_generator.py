import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from ai_brain.models import AIResponse, Context, Intent

load_dotenv()


class ResponseGenerator:
    """Generate grounded responses through a configurable Gemini model."""

    def __init__(self):
        self.provider = "gemini"
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
        try:
            self.client = genai.Client()
        except Exception:
            self.client = None

    def generate(self, user_message: str, intent: Intent, context: Context) -> AIResponse:
        if not self.client:
            return AIResponse(
                text="Sorry, I am having trouble connecting to the server. Please try again later.",
                reasoning="LLM client unavailable",
                provider=self.provider,
                model=self.model,
                latency_ms=0,
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
            response = self.client.models.generate_content(
                model=self.model,
                contents=f"User Message: {user_message}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=self.temperature,
                ),
            )
            reply = response.text or "I don't have enough information to answer that."
            note = f"Grounded on {len(context.knowledge_snippets)} knowledge snippets"
        except Exception as exc:
            reply = "An unexpected error occurred while processing your request."
            note = f"Generation error: {type(exc).__name__}"

        latency_ms = int((time.perf_counter() - started) * 1000)
        return AIResponse(
            text=reply.strip(),
            reasoning=note,
            provider=self.provider,
            model=self.model,
            latency_ms=latency_ms,
        )


generator = ResponseGenerator()
