from __future__ import annotations

import json
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


class _StableProbeClient:
    provider_name = "openai"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0

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
        response = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1
        return response

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


def test_cmd_run_propagates_timeout_and_retry_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_build_client(*, provider: str, timeout_seconds: int, reasoning_level: str) -> _DummyClient:
        captured["build_timeout"] = timeout_seconds
        captured["provider"] = provider
        captured["reasoning_level"] = reasoning_level
        return _DummyClient(provider)

    def _fake_run_benchmark(
        config: Any,
        client: Any = None,
        *,
        mentor_client: Any = None,
        worker_client: Any = None,
    ) -> dict[str, Any]:
        del client, mentor_client, worker_client
        captured["config"] = config
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
            "--model-timeout",
            "77",
            "--test-timeout",
            "19",
            "--model-retries",
            "2",
            "--model-retry-backoff",
            "1.5",
            "--results-path",
            str(tmp_path / "results.json"),
        ]
    )
    assert cli_module.cmd_run(args) == 0
    assert captured["build_timeout"] == 77
    assert captured["config"].timeout_seconds == 77
    assert captured["config"].test_timeout_seconds == 19
    assert captured["config"].model_retry_attempts == 2
    assert captured["config"].model_retry_backoff_seconds == 1.5


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


def test_cmd_preflight_passes_for_exact_stable_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "build_client",
        lambda *, provider, timeout_seconds, reasoning_level: _StableProbeClient(
            ["STABLE_OK", "STABLE_OK"]
        ),
    )

    parser = cli_module.build_parser()
    out_path = tmp_path / "preflight.json"
    args = parser.parse_args(
        [
            "preflight",
            "--provider",
            "openai",
            "--models",
            "gpt-5-mini",
            "--attempts",
            "2",
            "--out",
            str(out_path),
        ]
    )

    assert cli_module.cmd_preflight(args) == 0
    report = json.loads(out_path.read_text(encoding="utf-8"))
    assert report["models"][0]["stable"] is True
    output = capsys.readouterr().out
    assert "Backend preflight passed" in output


def test_cmd_preflight_fails_for_non_exact_or_inconsistent_response(
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
) -> None:
    monkeypatch.setattr(
        cli_module,
        "build_client",
        lambda *, provider, timeout_seconds, reasoning_level: _StableProbeClient(
            ["STABLE_OK", "stable ok"]
        ),
    )

    parser = cli_module.build_parser()
    args = parser.parse_args(
        [
            "preflight",
            "--provider",
            "openai",
            "--models",
            "gpt-5-mini",
            "--attempts",
            "2",
        ]
    )

    assert cli_module.cmd_preflight(args) == 1
    output = capsys.readouterr().out
    assert "UNSTABLE" in output
    assert "do not claim strict reproducibility" in output


def test_cmd_analyze_writes_deterministic_analysis(tmp_path: Path) -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "results_two_replicates.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "analysis.json"
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    parser = cli_module.build_parser()
    args = parser.parse_args(
        [
            "analyze",
            "--results",
            str(results_path),
            "--out",
            str(out_path),
            "--bootstrap-samples",
            "512",
        ]
    )

    assert cli_module.cmd_analyze(args) == 0
    analysis = json.loads(out_path.read_text(encoding="utf-8"))
    assert analysis["group_count"] >= 1
    assert analysis["bootstrap_samples"] == 512


def test_cmd_run_uses_multi_seed_runner_when_seeds_provided(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_build_client(*, provider: str, timeout_seconds: int, reasoning_level: str) -> _DummyClient:
        del timeout_seconds, reasoning_level
        return _DummyClient(provider)

    def _fake_run_multi_seed_benchmark(
        config: Any,
        *,
        seeds: list[int],
        client: Any = None,
        mentor_client: Any = None,
        worker_client: Any = None,
    ) -> dict[str, Any]:
        del client, mentor_client, worker_client
        captured["config"] = config
        captured["seeds"] = seeds
        return {"summary": {"total_runs": 0, "runs_by_mode": {}}, "run_group_id": "group_test"}

    monkeypatch.setattr(cli_module, "build_client", _fake_build_client)
    monkeypatch.setattr(cli_module, "run_multi_seed_benchmark", _fake_run_multi_seed_benchmark)

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
            "dev50",
            "--seeds",
            "1337,2026,9001",
            "--results-path",
            str(tmp_path / "results.json"),
        ]
    )
    exit_code = cli_module.cmd_run(args)
    assert exit_code == 0
    assert captured["seeds"] == [1337, 2026, 9001]


def test_cmd_run_uses_replicates_to_generate_deterministic_seed_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def _fake_build_client(*, provider: str, timeout_seconds: int, reasoning_level: str) -> _DummyClient:
        del timeout_seconds, reasoning_level
        return _DummyClient(provider)

    def _fake_run_multi_seed_benchmark(
        config: Any,
        *,
        seeds: list[int],
        client: Any = None,
        mentor_client: Any = None,
        worker_client: Any = None,
    ) -> dict[str, Any]:
        del config, client, mentor_client, worker_client
        captured["seeds"] = list(seeds)
        return {"summary": {"total_runs": 0, "runs_by_mode": {}}, "run_group_id": "group_test"}

    monkeypatch.setattr(cli_module, "build_client", _fake_build_client)
    monkeypatch.setattr(cli_module, "run_multi_seed_benchmark", _fake_run_multi_seed_benchmark)

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
            "dev50",
            "--seed",
            "1337",
            "--replicates",
            "3",
            "--results-path",
            str(tmp_path / "results.json"),
        ]
    )
    assert cli_module.cmd_run(args) == 0
    assert captured["seeds"] == [1337, 1577407918, 3794984304]


def test_cmd_run_rejects_conflicting_replicates_and_seeds(tmp_path: Path) -> None:
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
            "dev50",
            "--seed",
            "1337",
            "--seeds",
            "1337,2026",
            "--replicates",
            "2",
            "--results-path",
            str(tmp_path / "results.json"),
        ]
    )
    assert cli_module.cmd_run(args) == 1


def test_cmd_healthcheck_reports_metrics(tmp_path: Path, capsys: Any) -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "results_two_replicates.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    results_path = tmp_path / "results.json"
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    parser = cli_module.build_parser()
    args = parser.parse_args(["healthcheck", "--results", str(results_path)])
    assert cli_module.cmd_healthcheck(args) == 0
    output = capsys.readouterr().out
    assert "Benchmark Healthcheck" in output
    assert "Task difficulty distribution" in output
    assert "Pass-rate histogram" in output
    assert "Baseline variance across seeds" in output
    assert "Mentor lift distribution" in output


def test_cmd_healthcheck_warns_when_benchmark_is_too_easy(tmp_path: Path, capsys: Any) -> None:
    payload = {
        "runs": [
            {
                "mode": "worker_only",
                "seed": 1337,
                "worker_model": "worker-a",
                "task_id": f"task_{index:03d}",
                "task_difficulty": "easy",
                "pass": True,
            }
            for index in range(10)
        ]
    }
    results_path = tmp_path / "too_easy.json"
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    parser = cli_module.build_parser()
    args = parser.parse_args(["healthcheck", "--results", str(results_path)])
    assert cli_module.cmd_healthcheck(args) == 0
    output = capsys.readouterr().out
    assert "WARNING: Benchmark may be too easy" in output


def test_cmd_healthcheck_warns_when_benchmark_is_too_hard(tmp_path: Path, capsys: Any) -> None:
    payload = {
        "runs": [
            {
                "mode": "worker_only",
                "seed": 1337,
                "worker_model": "worker-a",
                "task_id": f"task_{index:03d}",
                "task_difficulty": "hard",
                "pass": False,
            }
            for index in range(10)
        ]
    }
    results_path = tmp_path / "too_hard.json"
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    parser = cli_module.build_parser()
    args = parser.parse_args(["healthcheck", "--results", str(results_path)])
    assert cli_module.cmd_healthcheck(args) == 0
    output = capsys.readouterr().out
    assert "WARNING: Benchmark may be too hard" in output


def test_audit_baseline_reuse_ignores_tiny_groups() -> None:
    runs = [
        {
            "mode": "worker_only",
            "seed": 1337,
            "worker_model": "worker-a",
            "task_id": "task_001",
            "pass": False,
            "patch_hash": "",
        },
        {
            "mode": "worker_only",
            "seed": 2026,
            "worker_model": "worker-a",
            "task_id": "task_001",
            "pass": False,
            "patch_hash": "",
        },
    ]
    ok, _ = cli_module._audit_baseline_reuse(runs)
    assert ok is True


def test_audit_baseline_reuse_flags_large_identical_vectors() -> None:
    runs: list[dict[str, Any]] = []
    for seed in (1337, 2026):
        for index in range(5):
            runs.append(
                {
                    "mode": "worker_only",
                    "seed": seed,
                    "worker_model": "worker-a",
                    "task_id": f"task_{index:03d}",
                    "pass": bool(index % 2),
                    "patch_hash": f"hash_{index}",
                }
            )
    ok, detail = cli_module._audit_baseline_reuse(runs)
    assert ok is False
    assert "Potential artifact reuse detected" in detail
