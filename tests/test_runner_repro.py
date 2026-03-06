from __future__ import annotations

import json
from pathlib import Path

import pytest

import mentor_worker_benchmark.runner as runner_module
from mentor_worker_benchmark.runner import BenchmarkConfig, run_benchmark, run_multi_seed_benchmark
from mentor_worker_benchmark.tasks.task_base import TaskDefinition
from mentor_worker_benchmark.tasks.task_codegen_py.harness import TestRunResult as HarnessTestRunResult
from mentor_worker_benchmark.tasks.task_registry import TaskSelection


class _FakeClient:
    provider_name = "openai"

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
        return "--- src/solution.py\n+++ src/solution.py\n@@ -1 +1 @@\n-print('bad')\n+print('good')\n"

    def runtime_metadata(self, model_names: list[str]) -> dict[str, object]:
        return {
            "model_tags": [
                {"id": name, "name": name, "digest": f"digest-{name}"}
                for name in model_names
            ]
        }


def _write_minimal_task(tmp_path: Path, *, task_id: str = "repro_task_000") -> TaskDefinition:
    task_root = tmp_path / task_id
    (task_root / "src").mkdir(parents=True, exist_ok=True)
    (task_root / "tests").mkdir(parents=True, exist_ok=True)
    (task_root / "prompt.md").write_text("# prompt\n", encoding="utf-8")
    (task_root / "src" / "solution.py").write_text("print('bad')\n", encoding="utf-8")
    (task_root / "tests" / "test_solution.py").write_text("def test_placeholder(): assert True\n", encoding="utf-8")
    return TaskDefinition(
        task_id=task_id,
        title="repro",
        category="logic",
        split="dev",
        difficulty="easy",
        pack_name="task_pack_v2",
        quick=True,
        path=task_root,
    )


def _selection_for_task(task: TaskDefinition) -> TaskSelection:
    return _selection_for_tasks([task])


def _selection_for_tasks(tasks: list[TaskDefinition]) -> TaskSelection:
    return TaskSelection(
        task_pack="task_pack_v2",
        selector_source="suite",
        suite="quick",
        tasks=list(tasks),
        pack_version="2.1.0",
        pack_source="registry",
        pack_license="MIT",
        pack_hash="a" * 64,
        pack_manifest_path="mentor_worker_benchmark/tasks/task_pack_v2/metadata.json",
    )


def test_run_benchmark_reproducibility_hash_stable_across_repeated_runs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    task = _write_minimal_task(tmp_path)
    monkeypatch.setattr(runner_module, "resolve_tasks", lambda **_: _selection_for_task(task))
    monkeypatch.setattr(runner_module, "_capture_pip_freeze_hash", lambda: ("a" * 64, 10))
    monkeypatch.setattr(runner_module, "_git_commit_hash", lambda: "de5a929")
    monkeypatch.setattr(runner_module, "_git_is_dirty", lambda: False)

    run_index = {"value": 0}

    def _run_once() -> dict[str, object]:
        run_index["value"] += 1
        calls = {"count": 0}
        suffix = 100 + run_index["value"] * 10

        def _fake_run_pytest(_workdir: Path, **_kwargs: object) -> HarnessTestRunResult:
            calls["count"] += 1
            if calls["count"] == 1:
                return HarnessTestRunResult(
                    exit_code=1,
                    passed=False,
                    output=(
                        "tmp_path = PosixPath("
                        f"'/private/var/folders/x/pytest-of-user/pytest-{suffix}/test_case0'"
                        ")\n1 failed in 0.01s"
                    ),
                    duration_seconds=0.01,
                    tests_executed=1,
                    tests_passed=0,
                    tests_failed=1,
                    timed_out=False,
                )
            return HarnessTestRunResult(
                exit_code=0,
                passed=True,
                output=(
                    "tmp_path = PosixPath("
                    f"'/private/var/folders/x/pytest-of-user/pytest-{suffix + 1}/test_case0'"
                    ")\n1 passed in 0.03s"
                ),
                duration_seconds=0.01,
                tests_executed=1,
                tests_passed=1,
                tests_failed=0,
                timed_out=False,
            )

        monkeypatch.setattr(runner_module, "run_pytest", _fake_run_pytest)

        config = BenchmarkConfig(
            models=["gpt-5-mini"],
            mentor_models_override=["gpt-5"],
            worker_models_override=["gpt-5-mini"],
            provider="openai",
            mentor_provider="openai",
            worker_provider="openai",
            run_modes=("worker_only",),
            task_pack="task_pack_v2",
            suite="quick",
            seed=1337,
            repro_mode=True,
            results_path=tmp_path / "results.json",
        )
        return run_benchmark(
            config,
            mentor_client=_FakeClient(),
            worker_client=_FakeClient(),
            write_outputs=False,
        )

    first = _run_once()
    second = _run_once()

    first_repro = first["reproducibility"]
    second_repro = second["reproducibility"]
    assert first_repro["deterministic_output_sha256"] == second_repro["deterministic_output_sha256"]
    assert first_repro["seed_policy"] == "deterministic"
    assert "<TMP_PATH>" in first["runs"][0]["log"]["initial_test_output"]
    assert "pytest-" not in first["runs"][0]["log"]["initial_test_output"]
    assert "0.01s" not in first["runs"][0]["log"]["initial_test_output"]
    assert "in <TIME>s" in first["runs"][0]["log"]["initial_test_output"]

    environment = first["environment"]
    assert environment["reproducibility"]["python_version"] == environment["python"]["version"]
    assert environment["reproducibility"]["cpu_architecture"] == environment["platform"]["machine"]
    assert environment["reproducibility"]["commit_hash"] == "de5a929"


def test_run_multi_seed_benchmark_recomputes_aggregates_across_replicates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def _fake_run_benchmark(
        config: BenchmarkConfig,
        client=None,
        *,
        mentor_client=None,
        worker_client=None,
        write_outputs=True,
        run_group_id=None,
    ) -> dict[str, object]:
        del client, mentor_client, worker_client, write_outputs
        baseline_pass = False
        mentored_pass = bool(config.seed == 2026)
        return {
            "generated_at": f"2026-03-05T00:00:0{0 if config.seed == 1337 else 1}+00:00",
            "run_group_id": run_group_id,
            "config": {
                "run_modes": ["worker_only", "mentor_worker"],
                "worker_models": ["gpt-5-mini"],
                "mentor_models": ["gpt-5"],
                "max_turns": 2,
                "timeout_seconds": 180,
                "generation": {"seed": int(config.seed)},
            },
            "summary": {"benchmark_wall_time_seconds": 0.0},
            "compute_budget": {
                "total_model_calls_attempted": 2,
                "total_tokens_estimate": 20,
                "total_wall_time_seconds": 0.0,
                "model_calls_attempted_by_mode": {"worker_only": 1, "mentor_worker": 1},
            },
            "runs": [
                {
                    "mode": "worker_only",
                    "task_id": "task_001",
                    "task_category": "logic",
                    "seed": int(config.seed),
                    "worker_model": "gpt-5-mini",
                    "mentor_model": None,
                    "pass": baseline_pass,
                    "turns_used": 1,
                    "tests_executed": 1,
                    "tests_passed": 0,
                    "tests_failed": 1,
                },
                {
                    "mode": "mentor_worker",
                    "task_id": "task_001",
                    "task_category": "logic",
                    "seed": int(config.seed),
                    "worker_model": "gpt-5-mini",
                    "mentor_model": "gpt-5",
                    "pass": mentored_pass,
                    "turns_used": 1,
                    "tests_executed": 1,
                    "tests_passed": 1 if mentored_pass else 0,
                    "tests_failed": 0 if mentored_pass else 1,
                },
            ],
            "violations": [],
            "environment": {},
            # Intentionally incorrect per-replicate aggregate to ensure merged output is recomputed.
            "aggregates": {
                "best_workers": [
                    {
                        "worker_model": "gpt-5-mini",
                        "baseline_pass_rate": 0.0,
                        "mentored_pass_rate": 0.0,
                        "control_pass_rate": 0.0,
                        "delta": 0.0,
                    }
                ],
                "best_mentors": [],
                "mentor_worker_pairs": [],
                "category_breakdown": [],
                "baseline_by_worker": {"gpt-5-mini": 0.0},
                "control_by_worker": {"gpt-5-mini": 0.0},
                "task_count": 1,
                "tasks": ["task_001"],
            },
        }

    monkeypatch.setattr(runner_module, "run_benchmark", _fake_run_benchmark)

    config = BenchmarkConfig(
        models=["gpt-5-mini"],
        mentor_models_override=["gpt-5"],
        worker_models_override=["gpt-5-mini"],
        provider="openai",
        mentor_provider="openai",
        worker_provider="openai",
        run_modes=("worker_only", "mentor_worker"),
        task_pack="task_pack_v2",
        suite="dev50",
        seed=1337,
        repro_mode=True,
        results_path=tmp_path / "results.json",
    )

    merged = run_multi_seed_benchmark(config, seeds=[1337, 2026])
    best_worker = merged["aggregates"]["best_workers"][0]
    assert best_worker["baseline_pass_rate"] == 0.0
    assert best_worker["mentored_pass_rate"] == 0.5
    assert best_worker["delta"] == 0.5
    assert (tmp_path / "results.seed-1337.json").exists()
    assert (tmp_path / "results.seed-2026.json").exists()


def test_run_benchmark_resumes_from_checkpoint_after_interruption(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tasks = [
        _write_minimal_task(tmp_path, task_id="resume_task_000"),
        _write_minimal_task(tmp_path, task_id="resume_task_001"),
    ]
    monkeypatch.setattr(runner_module, "resolve_tasks", lambda **_: _selection_for_tasks(tasks))
    monkeypatch.setattr(runner_module, "_capture_pip_freeze_hash", lambda: ("a" * 64, 10))
    monkeypatch.setattr(runner_module, "_git_commit_hash", lambda: "de5a929")
    monkeypatch.setattr(runner_module, "_git_is_dirty", lambda: False)

    interrupted = {"value": False}
    calls: list[str] = []

    def _fake_baseline_run(
        client,
        worker_model: str,
        task_prompt: str,
        task_id: str,
        task_family_id: str | None,
        worker_template: str,
        workdir: Path,
        generation,
        test_timeout_seconds: int,
        model_retry_attempts: int,
        model_retry_backoff_seconds: float,
    ) -> dict[str, object]:
        del client, task_prompt, task_family_id, worker_template, workdir, generation
        del test_timeout_seconds, model_retry_attempts, model_retry_backoff_seconds
        calls.append(task_id)
        if task_id == "resume_task_001" and not interrupted["value"]:
            interrupted["value"] = True
            raise KeyboardInterrupt("simulated stop")
        return {
            "mode": "worker_only",
            "task_id": task_id,
            "task_family_id": None,
            "seed": 1337,
            "evaluation_seed": 123,
            "worker_model": worker_model,
            "mentor_model": None,
            "pass": False,
            "turns_used": 1,
            "wall_time_seconds": 0.1,
            "total_tokens_estimate": 1,
            "patch_hash": None,
            "test_runtime_seconds": 0.1,
            "tests_executed": 1,
            "tests_passed": 0,
            "tests_failed": 1,
            "mentor_turn_count": 0,
            "mentor_violation_count": 0,
            "execution_evidence": {},
            "log": {
                "initial_test_output": "1 failed in 0.01s",
                "worker_prompt": "prompt",
                "worker_response": "",
                "worker_error": None,
                "worker_retry_count": 0,
                "extracted_patch": None,
                "patch_hash": None,
                "patch_length": 0,
                "patch_length_valid": False,
                "evaluation_seed": 123,
                "patch_applied": False,
                "patch_log": "No valid unified diff found in worker response.",
                "final_test_output": "1 failed in 0.01s",
                "initial_test_stats": {
                    "tests_executed": 1,
                    "tests_passed": 0,
                    "tests_failed": 1,
                    "duration_seconds": 0.1,
                },
                "final_test_stats": {
                    "tests_executed": 1,
                    "tests_passed": 0,
                    "tests_failed": 1,
                    "duration_seconds": 0.1,
                },
            },
        }

    monkeypatch.setattr(runner_module, "_baseline_run", _fake_baseline_run)

    config = BenchmarkConfig(
        models=["gpt-5-mini"],
        mentor_models_override=["gpt-5"],
        worker_models_override=["gpt-5-mini"],
        provider="openai",
        mentor_provider="openai",
        worker_provider="openai",
        run_modes=("worker_only",),
        task_pack="task_pack_v2",
        suite="quick",
        seed=1337,
        repro_mode=True,
        results_path=tmp_path / "results.json",
    )

    with pytest.raises(KeyboardInterrupt):
        run_benchmark(
            config,
            mentor_client=_FakeClient(),
            worker_client=_FakeClient(),
            write_outputs=False,
        )

    checkpoint_path = tmp_path / "results.checkpoint.jsonl"
    assert checkpoint_path.exists()
    lines = checkpoint_path.read_text(encoding="utf-8").splitlines()
    assert any("\"task_id\":\"resume_task_000\"" in line for line in lines)
    assert not any("\"task_id\":\"resume_task_001\"" in line for line in lines)

    resumed = run_benchmark(
        config,
        mentor_client=_FakeClient(),
        worker_client=_FakeClient(),
        write_outputs=False,
    )
    assert [run["task_id"] for run in resumed["runs"]] == ["resume_task_000", "resume_task_001"]
    assert calls == ["resume_task_000", "resume_task_001", "resume_task_001"]
    assert resumed["checkpointing"]["completed_units_loaded"] == 1
    assert resumed["checkpointing"]["completed_units_recorded"] == 1
    assert json.loads((tmp_path / "results.checkpoint.jsonl").read_text(encoding="utf-8").splitlines()[0])["event"] == "metadata"


def test_call_model_with_retries_retries_transient_runtime_errors(monkeypatch) -> None:
    calls = {"count": 0}
    backoffs: list[float] = []

    class _TransientClient:
        provider_name = "openai"

        def chat(self, **kwargs: object) -> str:
            del kwargs
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("request timed out while waiting for backend")
            return "STABLE_OK"

        def runtime_metadata(self, model_names: list[str]) -> dict[str, object]:
            del model_names
            return {}

    monkeypatch.setattr(runner_module.time, "sleep", lambda seconds: backoffs.append(seconds))

    response, error, retries_used = runner_module._call_model_with_retries(
        client=_TransientClient(),
        retry_attempts=1,
        retry_backoff_seconds=0.5,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hi"}],
    )

    assert response == "STABLE_OK"
    assert error is None
    assert retries_used == 1
    assert calls["count"] == 2
    assert backoffs == [0.5]


def test_call_model_with_retries_does_not_retry_non_transient_runtime_errors() -> None:
    calls = {"count": 0}

    class _PermanentFailureClient:
        provider_name = "openai"

        def chat(self, **kwargs: object) -> str:
            del kwargs
            calls["count"] += 1
            raise RuntimeError("invalid api key")

        def runtime_metadata(self, model_names: list[str]) -> dict[str, object]:
            del model_names
            return {}

    response, error, retries_used = runner_module._call_model_with_retries(
        client=_PermanentFailureClient(),
        retry_attempts=3,
        retry_backoff_seconds=0.5,
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hi"}],
    )

    assert response == ""
    assert error == "invalid api key"
    assert retries_used == 0
    assert calls["count"] == 1
