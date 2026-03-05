from __future__ import annotations

from pathlib import Path

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


def _write_minimal_task(tmp_path: Path) -> TaskDefinition:
    task_root = tmp_path / "task_000"
    (task_root / "src").mkdir(parents=True, exist_ok=True)
    (task_root / "tests").mkdir(parents=True, exist_ok=True)
    (task_root / "prompt.md").write_text("# prompt\n", encoding="utf-8")
    (task_root / "src" / "solution.py").write_text("print('bad')\n", encoding="utf-8")
    (task_root / "tests" / "test_solution.py").write_text("def test_placeholder(): assert True\n", encoding="utf-8")
    return TaskDefinition(
        task_id="repro_task_000",
        title="repro",
        category="logic",
        split="dev",
        difficulty="easy",
        pack_name="task_pack_v2",
        quick=True,
        path=task_root,
    )


def _selection_for_task(task: TaskDefinition) -> TaskSelection:
    return TaskSelection(
        task_pack="task_pack_v2",
        selector_source="suite",
        suite="quick",
        tasks=[task],
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
