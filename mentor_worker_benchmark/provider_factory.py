from __future__ import annotations

from mentor_worker_benchmark.llm_client import LLMClient
from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.openai_client import OpenAIClient

SUPPORTED_PROVIDERS = ("ollama", "openai")


def normalize_provider_name(raw: str) -> str:
    value = raw.strip().lower()
    if value not in SUPPORTED_PROVIDERS:
        allowed = ", ".join(SUPPORTED_PROVIDERS)
        raise ValueError(f"Unknown provider `{raw}`. Allowed values: {allowed}")
    return value


def build_client(
    *,
    provider: str,
    timeout_seconds: int,
    reasoning_level: str = "none",
) -> LLMClient:
    resolved_provider = normalize_provider_name(provider)
    if resolved_provider == "ollama":
        return OllamaClient(timeout_seconds=timeout_seconds)
    return OpenAIClient(timeout_seconds=timeout_seconds, reasoning_level=reasoning_level)
