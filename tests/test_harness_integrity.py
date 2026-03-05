from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import mentor_worker_benchmark.cli as cli_module
import mentor_worker_benchmark.runner as runner_module
from mentor_worker_benchmark.runner import BenchmarkConfig, run_benchmark
from mentor_worker_benchmark.tasks.task_base import TaskDefinition
from mentor_worker_benchmark.tasks.task_codegen_py.harness import TestRunResult as HarnessTestRunResult
from mentor_worker_benchmark.tasks.task_registry import TaskSelection


class _FakeClient:
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
        return {"model_names": model_names}


def _write_minimal_task(tmp_path: Path) -> TaskDefinition:
    task_root = tmp_path / "task_000"
    (task_root / "src").mkdir(parents=True, exist_ok=True)
    (task_root / "tests").mkdir(parents=True, exist_ok=True)
    (task_root / "prompt.md").write_text("# prompt\n", encoding="utf-8")
    (task_root / "src" / "solution.py").write_text("print('bad')\n", encoding="utf-8")
    (task_root / "tests" / "test_solution.py").write_text("def test_placeholder(): assert True\n", encoding="utf-8")
    return TaskDefinition(
        task_id="integrity_task_000",
        title="integrity",
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
        pack_version="2.0.0",
        pack_source="registry",
        pack_license="MIT",
        pack_hash="a" * 64,
        pack_manifest_path="mentor_worker_benchmark/tasks/task_pack_v2/metadata.json",
    )


def test_guard_aborts_when_no_tests_execute(monkeypatch, tmp_path: Path) -> None:
    task = _write_minimal_task(tmp_path)
    monkeypatch.setattr(runner_module, "resolve_tasks", lambda **_: _selection_for_task(task))
    monkeypatch.setattr(
        runner_module,
        "run_pytest",
        lambda _workdir, **_kwargs: HarnessTestRunResult(
            exit_code=1,
            passed=False,
            output="no tests ran in 0.01s",
            duration_seconds=0.01,
            tests_executed=0,
            tests_passed=0,
            tests_failed=0,
            timed_out=False,
        ),
    )

    config = BenchmarkConfig(
        models=["qwen2.5-coder:7b"],
        mentor_models_override=["llama3.1:8b"],
        worker_models_override=["qwen2.5-coder:7b"],
        run_modes=("worker_only",),
        task_pack="task_pack_v2",
        suite="quick",
        seed=1337,
        results_path=tmp_path / "results.json",
    )
    try:
        run_benchmark(config, mentor_client=_FakeClient(), worker_client=_FakeClient(), write_outputs=False)
    except RuntimeError as exc:
        assert "No tests executed for task" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected run_benchmark to abort when tests_executed == 0")


def test_quick_run_simulation_records_integrity_and_audit_passes(monkeypatch, tmp_path: Path, capsys) -> None:
    task = _write_minimal_task(tmp_path)
    monkeypatch.setattr(runner_module, "resolve_tasks", lambda **_: _selection_for_task(task))
    head_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    monkeypatch.setattr(runner_module, "_git_commit_hash", lambda: head_commit)
    monkeypatch.setattr(runner_module, "_git_is_dirty", lambda: False)

    calls = {"count": 0}

    def _fake_run_pytest(_workdir: Path, **_kwargs: object) -> HarnessTestRunResult:
        calls["count"] += 1
        if calls["count"] == 1:
            return HarnessTestRunResult(
                exit_code=1,
                passed=False,
                output="1 failed in 0.25s",
                duration_seconds=0.25,
                tests_executed=1,
                tests_passed=0,
                tests_failed=1,
                timed_out=False,
            )
        return HarnessTestRunResult(
            exit_code=0,
            passed=True,
            output="1 passed in 0.22s",
            duration_seconds=0.22,
            tests_executed=1,
            tests_passed=1,
            tests_failed=0,
            timed_out=False,
        )

    monkeypatch.setattr(runner_module, "run_pytest", _fake_run_pytest)

    results_path = tmp_path / "results.json"
    config = BenchmarkConfig(
        models=["qwen2.5-coder:7b"],
        mentor_models_override=["llama3.1:8b"],
        worker_models_override=["qwen2.5-coder:7b"],
        run_modes=("worker_only",),
        task_pack="task_pack_v2",
        suite="quick",
        seed=1337,
        results_path=results_path,
    )

    results = run_benchmark(config, mentor_client=_FakeClient(), worker_client=_FakeClient(), write_outputs=True)
    run = results["runs"][0]
    patch_text = run["log"]["extracted_patch"]
    assert isinstance(patch_text, str)
    assert run["tests_executed"] > 0
    assert run["tests_passed"] >= 0
    assert run["tests_failed"] >= 0
    assert run["patch_hash"] == hashlib.sha256(patch_text.encode("utf-8")).hexdigest()

    parser = cli_module.build_parser()
    args = parser.parse_args(["audit", str(results_path)])
    assert cli_module.cmd_audit(args) == 0
    output = capsys.readouterr().out
    assert "✓ real patches generated" in output
    assert "✓ tests executed" in output
    assert "✓ baseline computed" in output
    assert "✓ artifact integrity verified" in output
