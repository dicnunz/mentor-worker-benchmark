from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import mentor_worker_benchmark.cli as cli_module
from mentor_worker_benchmark.provider_factory import build_client, normalize_provider_name


class _DummyClient:
    def __init__(self, provider_name: str) -> None:
        self.provider_name = provider_name

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
        del model, messages, system, temperature, top_p, num_predict, seed
        return ""

    def runtime_metadata(self, model_names: list[str]) -> dict[str, Any]:
        return {"model_tags": [{"id": item} for item in model_names]}


def test_provider_normalization() -> None:
    assert normalize_provider_name("ollama") == "ollama"
    assert normalize_provider_name("OPENAI") == "openai"
    with pytest.raises(ValueError, match="Unknown provider"):
        normalize_provider_name("unsupported")


def test_build_client_openai_requires_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    client = build_client(provider="openai", timeout_seconds=30, reasoning_level="none")
    assert getattr(client, "provider_name") == "openai"


def test_cmd_run_supports_provider_overrides_and_single_model_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_build_client(*, provider: str, timeout_seconds: int, reasoning_level: str) -> _DummyClient:
        captured.setdefault("build_calls", []).append(
            {
                "provider": provider,
                "timeout_seconds": timeout_seconds,
                "reasoning_level": reasoning_level,
            }
        )
        return _DummyClient(provider)

    def _fake_run_benchmark(
        config: Any,
        client: Any = None,
        *,
        mentor_client: Any = None,
        worker_client: Any = None,
    ) -> dict[str, Any]:
        del client
        captured["config"] = config
        captured["mentor_client"] = mentor_client
        captured["worker_client"] = worker_client
        return {"summary": {"total_runs": 0, "runs_by_mode": {}}}

    monkeypatch.setattr(cli_module, "build_client", _fake_build_client)
    monkeypatch.setattr(cli_module, "run_benchmark", _fake_run_benchmark)

    parser = cli_module.build_parser()
    args = parser.parse_args(
        [
            "run",
            "--provider",
            "openai",
            "--mentor-model",
            "gpt-5",
            "--worker-model",
            "gpt-5-mini",
            "--suite",
            "quick",
            "--results-path",
            str(tmp_path / "results.json"),
        ]
    )
    exit_code = cli_module.cmd_run(args)
    assert exit_code == 0

    assert len(captured["build_calls"]) == 1
    assert captured["build_calls"][0]["provider"] == "openai"
    assert captured["config"].mentor_provider == "openai"
    assert captured["config"].worker_provider == "openai"
    assert captured["config"].mentor_models_override == ["gpt-5"]
    assert captured["config"].worker_models_override == ["gpt-5-mini"]


def test_cmd_run_rejects_conflicting_single_and_plural_model_flags(tmp_path: Path) -> None:
    parser = cli_module.build_parser()
    args = parser.parse_args(
        [
            "run",
            "--provider",
            "openai",
            "--mentor-model",
            "gpt-5",
            "--mentor-models",
            "gpt-5-mini,gpt-4.1-mini",
            "--results-path",
            str(tmp_path / "results.json"),
        ]
    )
    assert cli_module.cmd_run(args) == 1
