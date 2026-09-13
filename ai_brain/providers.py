import os
from dataclasses import dataclass
from typing import Protocol

from google import genai
from google.genai import types


@dataclass
class ProviderResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, *, prompt: str, system_instruction: str, temperature: float) -> ProviderResult: ...


class GeminiProvider:
    name = "gemini"

    def __init__(self):
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def generate(self, *, prompt: str, system_instruction: str, temperature: float) -> ProviderResult:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=temperature),
        )
        usage = getattr(response, "usage_metadata", None)
        return ProviderResult(
            text=response.text or "I don't have enough information to answer that.",
            input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
        )


class OfflineProvider:
    name = "offline"
    model = "offline-fallback-v1"

    def generate(self, *, prompt: str, system_instruction: str, temperature: float) -> ProviderResult:
        return ProviderResult(text="Sorry, I am having trouble connecting to the AI service. Please try again later.")


def get_llm_provider() -> LLMProvider:
    configured = os.getenv("LLM_PROVIDER", "gemini").lower()
    if configured == "gemini":
        try:
            return GeminiProvider()
        except Exception:
            return OfflineProvider()
    if configured == "offline":
        return OfflineProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER: {configured}")
