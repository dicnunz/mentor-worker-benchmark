from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    provider_name: str

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        system: str | None = None,
        temperature: float = 0.0,
        top_p: float = 1.0,
        num_predict: int = 512,
        seed: int | None = None,
    ) -> str:
        ...

    def runtime_metadata(self, model_names: list[str]) -> dict[str, Any]:
        ...
