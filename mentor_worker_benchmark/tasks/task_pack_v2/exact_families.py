from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

FAMILY_BASE_FILES = ("prompt.md", "starter_code.py")


def _as_bytes(value: str | bytes) -> bytes:
    if isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _family_relevant_paths(file_map: Mapping[str, str | bytes]) -> list[str]:
    selected: list[str] = []
    for rel_path in FAMILY_BASE_FILES:
        if rel_path in file_map:
            selected.append(rel_path)

    test_paths = [
        rel_path
        for rel_path in file_map
        if rel_path.startswith("tests/")
        and rel_path.endswith(".py")
        and "__pycache__" not in rel_path.split("/")
    ]
    selected.extend(sorted(test_paths))
    return selected


def compute_exact_family_hash_for_file_map(file_map: Mapping[str, str | bytes]) -> str:
    parts: list[bytes] = []
    for rel_path in _family_relevant_paths(file_map):
        parts.append(rel_path.encode("utf-8") + b"\0" + _as_bytes(file_map[rel_path]))
    return hashlib.sha256(b"\n\x1f".join(parts)).hexdigest()


def compute_exact_family_hash_for_task_dir(task_dir: Path) -> str:
    file_map: dict[str, bytes] = {}
    for rel_path in FAMILY_BASE_FILES:
        path = task_dir / rel_path
        if path.exists():
            file_map[rel_path] = path.read_bytes()

    tests_dir = task_dir / "tests"
    if tests_dir.exists():
        for path in sorted(tests_dir.rglob("*.py")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel_path = path.relative_to(task_dir).as_posix()
            file_map[rel_path] = path.read_bytes()

    return compute_exact_family_hash_for_file_map(file_map)
