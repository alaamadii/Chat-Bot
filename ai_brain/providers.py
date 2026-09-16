import os
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI


@dataclass
class ProviderResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, *, prompt: str, system_instruction: str, temperature: float) -> ProviderResult: ...


class OpenAIProvider:
    name = "openai"

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        self.client = OpenAI(api_key=api_key)

    def generate(self, *, prompt: str, system_instruction: str, temperature: float) -> ProviderResult:
        kwargs = {
            "model": self.model,
            "instructions": system_instruction,
            "input": prompt,
        }
        # Reasoning models may not accept arbitrary temperature values. Keep
        # temperature configurable but only send it when explicitly enabled.
        if os.getenv("OPENAI_USE_TEMPERATURE", "false").lower() == "true":
            kwargs["temperature"] = temperature
        response = self.client.responses.create(**kwargs)
        usage = getattr(response, "usage", None)
        return ProviderResult(
            text=(getattr(response, "output_text", None) or "I don't have enough information to answer that."),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )


class OfflineProvider:
    name = "offline"
    model = "offline-fallback-v1"

    def generate(self, *, prompt: str, system_instruction: str, temperature: float) -> ProviderResult:
        return ProviderResult(text="Sorry, I am having trouble connecting to the AI service. Please try again later.")


def get_llm_provider() -> LLMProvider:
    configured = os.getenv("LLM_PROVIDER", "openai").lower()
    if configured == "openai":
        try:
            return OpenAIProvider()
        except Exception:
            return OfflineProvider()
    if configured == "offline":
        return OfflineProvider()
    raise ValueError(f"Unsupported LLM_PROVIDER: {configured}")
