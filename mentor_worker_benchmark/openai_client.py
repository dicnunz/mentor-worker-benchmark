from __future__ import annotations

import os
from typing import Any

import requests


class OpenAIClient:
    """Minimal OpenAI Chat Completions client compatible with benchmark runner usage."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 120,
        reasoning_level: str | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for provider `openai`. "
                "Set it in your environment and retry."
            )

        self.api_key = resolved_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        level = (reasoning_level or "").strip().lower()
        self.reasoning_level = level if level and level != "none" else None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        system: str | None,
        temperature: float,
        top_p: float,
        num_predict: int,
        seed: int | None,
        include_reasoning: bool,
    ) -> dict[str, Any]:
        request_messages = list(messages)
        if system:
            request_messages = [{"role": "system", "content": system}] + request_messages

        payload: dict[str, Any] = {
            "model": model,
            "messages": request_messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_completion_tokens": num_predict,
        }
        if seed is not None:
            payload["seed"] = seed
        if include_reasoning and self.reasoning_level:
            payload["reasoning_effort"] = self.reasoning_level
        return payload

    @staticmethod
    def _is_reasoning_param_error(response: requests.Response) -> bool:
        if response.status_code < 400:
            return False
        try:
            body = response.json()
        except ValueError:
            return False
        error = body.get("error", {}) if isinstance(body, dict) else {}
        message = str(error.get("message", "")).lower()
        param = str(error.get("param", "")).lower()
        return "reasoning_effort" in message or param == "reasoning_effort"

    @staticmethod
    def _extract_content(body: dict[str, Any], model: str) -> str:
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError(f"Unexpected OpenAI response format for model `{model}`: {body}")
        first = choices[0]
        if not isinstance(first, dict):
            raise RuntimeError(f"Unexpected OpenAI response format for model `{model}`: {body}")
        message = first.get("message", {})
        if not isinstance(message, dict):
            raise RuntimeError(f"Unexpected OpenAI response format for model `{model}`: {body}")

        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return "".join(parts)
        raise RuntimeError(f"Unexpected OpenAI response format for model `{model}`: {body}")

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
        payload = self._build_payload(
            model=model,
            messages=messages,
            system=system,
            temperature=temperature,
            top_p=top_p,
            num_predict=num_predict,
            seed=seed,
            include_reasoning=True,
        )

        try:
            response = requests.post(
                self._url("/chat/completions"),
                headers=self._headers(),
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"OpenAI chat request failed for model `{model}`. "
                "Check OPENAI_API_KEY, network connectivity, and your account limits."
            ) from exc

        if self.reasoning_level and self._is_reasoning_param_error(response):
            fallback_payload = self._build_payload(
                model=model,
                messages=messages,
                system=system,
                temperature=temperature,
                top_p=top_p,
                num_predict=num_predict,
                seed=seed,
                include_reasoning=False,
            )
            try:
                response = requests.post(
                    self._url("/chat/completions"),
                    headers=self._headers(),
                    json=fallback_payload,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"OpenAI chat request failed for model `{model}`. "
                    "Check OPENAI_API_KEY, network connectivity, and your account limits."
                ) from exc

        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            detail: str | None = None
            try:
                payload_body = response.json()
            except ValueError:
                payload_body = None
            if isinstance(payload_body, dict):
                error = payload_body.get("error", {})
                if isinstance(error, dict):
                    message = error.get("message")
                    if isinstance(message, str) and message.strip():
                        detail = message.strip()
            suffix = f" ({detail})" if detail else ""
            raise RuntimeError(
                f"OpenAI chat request failed for model `{model}`{suffix}. "
                "Check model access, rate limits, and account credits."
            ) from exc

        body = response.json()
        return self._extract_content(body, model)

    def runtime_metadata(self, model_names: list[str]) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "reasoning_level": self.reasoning_level or "none",
            "model_tags": [{"id": name} for name in model_names],
        }
