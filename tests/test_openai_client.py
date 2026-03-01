from __future__ import annotations

import pytest

from mentor_worker_benchmark.openai_client import OpenAIClient


class _FakeResponse:
    def __init__(self, *, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_openai_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIClient()


def test_openai_chat_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    seen_payloads: list[dict] = []

    def _fake_post(url: str, *, headers: dict, json: dict, timeout: int) -> _FakeResponse:
        assert url.endswith("/chat/completions")
        assert headers["Authorization"].startswith("Bearer ")
        assert timeout == 42
        seen_payloads.append(json)
        return _FakeResponse(
            status_code=200,
            payload={"choices": [{"message": {"content": "```diff\n--- a\n+++ b\n@@\n```"}}]},
        )

    monkeypatch.setattr("mentor_worker_benchmark.openai_client.requests.post", _fake_post)

    client = OpenAIClient(timeout_seconds=42, reasoning_level="none")
    response = client.chat(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hello"}],
        system="system prompt",
        temperature=0.0,
        top_p=1.0,
        num_predict=321,
        seed=1337,
    )

    assert "```diff" in response
    payload = seen_payloads[0]
    assert payload["model"] == "gpt-5-mini"
    assert payload["max_completion_tokens"] == 321
    assert payload["seed"] == 1337
    assert "reasoning_effort" not in payload


def test_openai_chat_retries_without_reasoning_when_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    seen_payloads: list[dict] = []
    call_index = {"count": 0}

    def _fake_post(url: str, *, headers: dict, json: dict, timeout: int) -> _FakeResponse:
        del url, headers, timeout
        seen_payloads.append(json)
        call_index["count"] += 1
        if call_index["count"] == 1:
            return _FakeResponse(
                status_code=400,
                payload={
                    "error": {
                        "message": "Unknown parameter: reasoning_effort",
                        "param": "reasoning_effort",
                    }
                },
            )
        return _FakeResponse(
            status_code=200,
            payload={
                "choices": [
                    {"message": {"content": [{"type": "output_text", "text": "final answer"}]}}
                ]
            },
        )

    monkeypatch.setattr("mentor_worker_benchmark.openai_client.requests.post", _fake_post)

    client = OpenAIClient(reasoning_level="medium")
    output = client.chat(model="gpt-5", messages=[{"role": "user", "content": "hi"}])

    assert output == "final answer"
    assert len(seen_payloads) == 2
    assert seen_payloads[0]["reasoning_effort"] == "medium"
    assert "reasoning_effort" not in seen_payloads[1]
