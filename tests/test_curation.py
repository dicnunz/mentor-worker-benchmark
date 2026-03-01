from __future__ import annotations

from pathlib import Path

from mentor_worker_benchmark.tasks.task_pack_v1.curate import (
    _assign_difficulties,
    _target_difficulty_counts,
    _task_quality,
    TaskEntry,
)


def _entry(task_id: str, difficulty: str, prompt: str, tests: str, starter: str) -> TaskEntry:
    return TaskEntry(
        task_id=task_id,
        title=task_id,
        category="ds_algo",
        difficulty=difficulty,
        split="dev",
        quick=False,
        path=Path("/tmp") / task_id,
        prompt=prompt,
        tests=tests,
        starter=starter,
        metadata_row={
            "task_id": task_id,
            "title": task_id,
            "category": "ds_algo",
            "difficulty": difficulty,
            "split": "dev",
            "quick": False,
            "path": f"tasks/{task_id}",
        },
    )


def test_target_difficulty_counts() -> None:
    assert _target_difficulty_counts(300) == {"easy": 105, "medium": 135, "hard": 60}


def test_task_quality_flags_examples_and_edge_cases() -> None:
    entry = _entry(
        "v1_ds_algo_000",
        "medium",
        prompt="Example Input: records Output: sorted names",
        tests="""
from src.solution import rank_products

def test_a():
    assert rank_products([], 1) == []

def test_b():
    import pytest
    with pytest.raises(ValueError):
        raise ValueError("invalid")
""",
        starter="def rank_products(records, k):\n    return []\n",
    )
    quality = _task_quality(entry)
    assert quality.has_io_examples
    assert quality.has_boundary_tests
    assert quality.has_invalid_input_tests
    assert quality.test_count == 2


def test_assign_difficulties_respects_target_distribution() -> None:
    entries = {}
    for idx in range(300):
        task_id = f"v1_ds_algo_{idx:03d}"
        entries[task_id] = _entry(
            task_id,
            "medium",
            "Example Input: x Output: y",
            "def test_a():\n    assert True\n",
            "def solve():\n    return 1\n",
        )

    dev_scores = {task_id: (idx % 3) / 2 for idx, task_id in enumerate(sorted(entries)[:50])}
    assigned = _assign_difficulties(
        entries,
        seed=1337,
        dev_task_scores=dev_scores,
        bucket_avg={},
        category_avg={"ds_algo": 0.5},
    )

    counts = {"easy": 0, "medium": 0, "hard": 0}
    for value in assigned.values():
        counts[value] += 1
    assert counts == {"easy": 105, "medium": 135, "hard": 60}
