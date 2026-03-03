from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mentor_worker_benchmark.tasks.task_pack_validation as validation


def _write_synthetic_task(root: Path, *, weak_tests: bool) -> dict[str, Any]:
    task_dir = root / "tasks" / "tiny_task"
    src_dir = task_dir / "src"
    tests_dir = task_dir / "tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    (task_dir / "prompt.md").write_text(
        "Implement solve(values) and handle empty input.",
        encoding="utf-8",
    )
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "solution.py").write_text(
        "def solve(values):\n    return sum(values)\n",
        encoding="utf-8",
    )

    if weak_tests:
        test_text = "def test_smoke():\n    assert True\n"
    else:
        test_text = (
            "from src.solution import solve\n\n"
            "def test_sum_values():\n"
            "    assert solve([1, 2, 3]) == 6\n"
            "def test_empty_values_boundary():\n"
            "    assert solve([]) == 0\n"
        )
    (tests_dir / "test_solution.py").write_text(test_text, encoding="utf-8")

    return {
        "pack_name": "synthetic_pack",
        "pack_version": "0.0.1",
        "counts": {
            "total": 1,
            "train": 1,
            "dev": 0,
            "test": 0,
            "quick": 0,
        },
        "categories": ["synthetic"],
        "tasks": [
            {
                "task_id": "tiny_task",
                "title": "Tiny task",
                "category": "synthetic",
                "difficulty": "easy",
                "split": "train",
                "quick": False,
                "path": "tasks/tiny_task",
            }
        ],
    }


def test_mutate_source_with_wrong_patch_changes_function_body() -> None:
    source_text = "def solve(values):\n    return sum(values)\n"
    mutated, target, reason = validation.mutate_source_with_wrong_patch(
        task_id="tiny_task",
        module_name="solution",
        source_text=source_text,
        symbol_hints={"solve"},
    )
    assert reason is None
    assert target is not None
    assert target["module"] == "solution"
    assert target["symbol"] == "solve"
    assert mutated is not None
    assert mutated != source_text
    assert (
        "return None" in mutated
        or "return 0" in mutated
        or "RuntimeError" in mutated
    )


def test_validate_task_pack_payload_strict_flags_not_caught_mutation(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    payload = _write_synthetic_task(tmp_path, weak_tests=True)
    schema = {"type": "object"}
    monkeypatch.setitem(
        validation.PACK_EXPECTATIONS,
        "synthetic_pack",
        {
            "total": 1,
            "splits": {"train": 1, "dev": 0, "test": 0},
            "quick": 0,
            "difficulty": {"easy": 1, "medium": 0, "hard": 0},
            "strength_policy": {
                "min_strength_score": 0,
                "max_low_strength_fraction": 1.0,
                "max_mutation_skip_fraction": 1.0,
                "require_mutation_caught": True,
            },
        },
    )

    ok, errors, report = validation.validate_task_pack_payload(
        root=tmp_path,
        payload=payload,
        schema=schema,
        strict=True,
        return_report=True,
        mutation_sample_limit=1,
    )
    assert not ok
    assert any("Strength gate failure" in item for item in errors)
    strict_eval = report["strength_gates"]["strict_evaluation"]
    assert strict_eval["would_fail"] is True
    assert strict_eval["mutation_not_caught_non_allowlisted_ids"] == ["tiny_task"]

