from __future__ import annotations

import json
from pathlib import Path

from mentor_worker_benchmark.packs.registry import get_pack_card, load_pack_registry
from mentor_worker_benchmark.tasks.task_registry import compute_external_pack_hash, resolve_tasks


def _write_external_pack(root: Path) -> Path:
    pack_root = root / "external_pack"
    task_dir = pack_root / "tasks" / "ext_task_001"
    src_dir = task_dir / "src"
    tests_dir = task_dir / "tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    (task_dir / "prompt.md").write_text(
        "Implement solve(values) to return the sum of integer values.",
        encoding="utf-8",
    )
    (src_dir / "__init__.py").write_text("", encoding="utf-8")
    (src_dir / "solution.py").write_text(
        "def solve(values):\n    return sum(values)\n",
        encoding="utf-8",
    )
    (tests_dir / "test_solution.py").write_text(
        "from src.solution import solve\n\n"
        "def test_sum_values():\n"
        "    assert solve([1, 2, 3]) == 6\n\n"
        "def test_empty_boundary_case():\n"
        "    assert solve([]) == 0\n\n"
        "def test_negative_values():\n"
        "    assert solve([-1, 1]) == 0\n",
        encoding="utf-8",
    )

    metadata = {
        "pack_name": "external_demo_pack",
        "pack_version": "0.1.0",
        "license": "MIT",
        "counts": {
            "total": 1,
            "train": 0,
            "dev": 1,
            "test": 0,
            "quick": 1,
        },
        "categories": ["external_demo"],
        "tasks": [
            {
                "task_id": "ext_task_001",
                "title": "External task",
                "category": "external_demo",
                "difficulty": "easy",
                "split": "dev",
                "quick": True,
                "path": "tasks/ext_task_001",
            }
        ],
    }
    (pack_root / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return pack_root


def test_registry_contains_default_pack_cards() -> None:
    registry = load_pack_registry()
    assert isinstance(registry.get("packs"), list)
    assert get_pack_card("task_pack_v1") is not None
    assert get_pack_card("task_pack_v2") is not None


def test_resolve_tasks_supports_registry_module_alias() -> None:
    selection = resolve_tasks(
        task_pack="mentor_worker_benchmark.tasks.task_pack_v2",
        suite="quick",
        legacy_selector=None,
        seed=1337,
    )
    assert selection.task_pack == "task_pack_v2"
    assert selection.pack_source in {"registry", "builtin"}
    assert len(selection.tasks) == 30


def test_external_pack_hash_is_deterministic_and_sensitive(tmp_path: Path) -> None:
    pack_root = _write_external_pack(tmp_path)
    first = compute_external_pack_hash(pack_root)
    second = compute_external_pack_hash(pack_root)
    assert first == second

    solution_path = pack_root / "tasks" / "ext_task_001" / "src" / "solution.py"
    solution_path.write_text("def solve(values):\n    return 0\n", encoding="utf-8")
    changed = compute_external_pack_hash(pack_root)
    assert changed != first


def test_resolve_tasks_external_pack_path_returns_pack_hash(tmp_path: Path) -> None:
    pack_root = _write_external_pack(tmp_path)
    selection = resolve_tasks(
        task_pack="task_pack_v2",
        task_pack_path=pack_root,
        suite="quick",
        legacy_selector=None,
        seed=1337,
    )
    assert selection.task_pack == "external_demo_pack"
    assert selection.pack_source == "external"
    assert isinstance(selection.pack_hash, str) and len(selection.pack_hash) == 64
    assert selection.pack_license == "MIT"
    assert len(selection.tasks) == 1
