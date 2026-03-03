from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.packs.registry import get_pack_card, list_pack_cards
from mentor_worker_benchmark.tasks.task_base import TaskDefinition
from mentor_worker_benchmark.tasks.task_codegen_py.task_defs import select_tasks as select_legacy_tasks
from mentor_worker_benchmark.tasks.task_pack_v1.pack import (
    load_task_pack_v1,
    read_pack_metadata as read_pack_v1_metadata,
)
from mentor_worker_benchmark.tasks.task_pack_v2.pack import (
    load_task_pack_v2,
    read_pack_metadata as read_pack_v2_metadata,
)
from mentor_worker_benchmark.tasks.task_pack_validation import validate_task_pack_payload


@dataclass(frozen=True, slots=True)
class TaskSelection:
    task_pack: str
    selector_source: str
    suite: str
    tasks: list[TaskDefinition]
    pack_version: str | None = None
    pack_source: str = "builtin"
    pack_license: str | None = None
    pack_hash: str | None = None
    pack_manifest_path: str | None = None


def _registry_card(pack_id: str) -> dict[str, Any]:
    card = get_pack_card(pack_id)
    return card if isinstance(card, dict) else {}


def _normalize_task_pack_identifier(task_pack: str) -> str:
    card = get_pack_card(task_pack)
    if isinstance(card, dict):
        card_id = card.get("pack_id")
        if isinstance(card_id, str) and card_id:
            return card_id

    aliases = {
        "mentor_worker_benchmark.tasks.task_codegen_py": "task_codegen_py",
        "mentor_worker_benchmark.tasks.task_codegen_py.task_defs": "task_codegen_py",
        "legacy_codegen_py": "task_codegen_py",
    }
    return aliases.get(task_pack, task_pack)


def _select_by_explicit_ids(tasks: list[TaskDefinition], selector: str) -> list[TaskDefinition]:
    by_id = {task.task_id: task for task in tasks}
    selected: list[TaskDefinition] = []
    for item in [entry.strip() for entry in selector.split(",") if entry.strip()]:
        if item not in by_id:
            known = ", ".join(sorted(by_id))
            raise ValueError(f"Unknown task id `{item}`. Known tasks: {known}")
        selected.append(by_id[item])
    if not selected:
        raise ValueError("No tasks selected.")
    return selected


def _stable_shuffle(tasks: list[TaskDefinition], seed: int) -> list[TaskDefinition]:
    ordered = list(tasks)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    return ordered


def _balanced_split_sample(
    tasks: list[TaskDefinition],
    *,
    split: str,
    target_count: int,
    seed: int,
) -> list[TaskDefinition]:
    split_tasks = [task for task in tasks if task.split == split]
    if not split_tasks:
        raise ValueError(f"No tasks found for split `{split}`.")

    by_category: dict[str, list[TaskDefinition]] = {}
    for task in split_tasks:
        by_category.setdefault(task.category, []).append(task)

    category_names = sorted(by_category)
    queues: list[list[TaskDefinition]] = []
    for index, category in enumerate(category_names):
        ordered = sorted(by_category[category], key=lambda item: item.task_id)
        shuffled = _stable_shuffle(ordered, seed + (index + 1) * 101)
        queues.append(shuffled)

    picks: list[TaskDefinition] = []
    while len(picks) < target_count:
        progressed = False
        for queue in queues:
            if not queue:
                continue
            picks.append(queue.pop(0))
            progressed = True
            if len(picks) >= target_count:
                break
        if not progressed:
            break

    if len(picks) < target_count:
        raise ValueError(
            f"Unable to select {target_count} tasks for split `{split}`; only found {len(picks)}."
        )
    return picks


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _generic_suite_selection(
    *,
    tasks: list[TaskDefinition],
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> tuple[list[TaskDefinition], str, str]:
    def _quick_suite() -> list[TaskDefinition]:
        quick_flagged = [task for task in tasks if task.quick]
        if quick_flagged:
            ordered = sorted(quick_flagged, key=lambda task: task.task_id)
            return _stable_shuffle(ordered, seed)
        raise ValueError("Quick suite selection found no tasks marked with `quick=true`.")

    if legacy_selector:
        if legacy_selector == "all":
            selected = tasks
            selector_source = "tasks"
            suite_label = "all"
        elif legacy_selector == "quick":
            selected = _quick_suite()
            selector_source = "tasks"
            suite_label = "quick"
        else:
            selected = _select_by_explicit_ids(tasks, legacy_selector)
            selector_source = "tasks"
            suite_label = "explicit"
    else:
        selector_source = "suite"
        suite_token = suite or "dev,test"
        suite_label = suite_token

        if suite_token == "all":
            selected = tasks
        elif suite_token == "quick":
            selected = _quick_suite()
        elif suite_token == "dev10":
            selected = _balanced_split_sample(tasks, split="dev", target_count=10, seed=seed)
        elif suite_token == "dev50":
            selected = _balanced_split_sample(tasks, split="dev", target_count=50, seed=seed)
        else:
            split_tokens = {token.strip() for token in suite_token.split(",") if token.strip()}
            valid = {"train", "dev", "test"}
            if not split_tokens:
                raise ValueError("Suite selector resolved to no splits.")
            if not split_tokens.issubset(valid):
                bad = ", ".join(sorted(split_tokens - valid))
                raise ValueError(
                    f"Unsupported suite token(s): {bad}. Use quick, dev10, dev50, dev, test, all."
                )
            selected = [task for task in tasks if task.split in split_tokens]

    if not selected:
        raise ValueError("Task selection produced zero tasks.")

    return _stable_shuffle(selected, seed=seed), selector_source, suite_label


def _build_external_expected(payload: dict[str, Any]) -> dict[str, Any]:
    counts = payload.get("counts", {})
    tasks = payload.get("tasks", [])
    expected: dict[str, Any] = {}

    if isinstance(tasks, list):
        expected["total"] = int(counts.get("total", len(tasks))) if isinstance(counts, dict) else len(tasks)

    if isinstance(counts, dict):
        expected["splits"] = {
            "train": int(counts.get("train", 0)),
            "dev": int(counts.get("dev", 0)),
            "test": int(counts.get("test", 0)),
        }
        expected["quick"] = int(counts.get("quick", 0))

    difficulty_counts = payload.get("difficulty_counts")
    if isinstance(difficulty_counts, dict):
        if all(key in difficulty_counts for key in ("easy", "medium", "hard")):
            expected["difficulty"] = {
                "easy": int(difficulty_counts.get("easy", 0)),
                "medium": int(difficulty_counts.get("medium", 0)),
                "hard": int(difficulty_counts.get("hard", 0)),
            }

    return expected


def compute_external_pack_hash(pack_root: Path) -> str:
    manifest_path = (pack_root / "metadata.json").resolve()
    if not manifest_path.exists():
        raise RuntimeError(f"External pack manifest not found: {manifest_path}")
    if not _is_within_root(manifest_path, pack_root):
        raise RuntimeError("External pack manifest must be inside the pack root.")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("External pack metadata.json must contain a JSON object.")

    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list):
        raise RuntimeError("External pack metadata.json `tasks` must be a list.")

    hasher = hashlib.sha256()
    manifest_bytes = manifest_path.read_bytes()
    hasher.update(b"manifest\0")
    hasher.update(manifest_bytes)

    file_entries: list[tuple[str, Path]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        rel_path = str(task.get("path", ""))
        task_dir = (pack_root / rel_path).resolve()
        if not _is_within_root(task_dir, pack_root):
            raise RuntimeError(f"Unsafe task path outside pack root: {rel_path}")
        if not task_dir.exists():
            raise RuntimeError(f"Task path missing for hash computation: {task_dir}")
        for file_path in sorted(path for path in task_dir.rglob("*") if path.is_file()):
            rel = file_path.resolve().relative_to(pack_root.resolve()).as_posix()
            file_entries.append((rel, file_path))

    for rel, file_path in sorted(file_entries):
        hasher.update(b"file\0")
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_path.read_bytes())

    return hasher.hexdigest()


def _load_external_pack(
    *,
    pack_root: Path,
) -> tuple[dict[str, Any], list[TaskDefinition], str]:
    root = pack_root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"External task pack path does not exist or is not a directory: {pack_root}")

    manifest_path = root / "metadata.json"
    if not manifest_path.exists():
        raise ValueError(f"External task pack is missing metadata.json: {manifest_path}")

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"External task pack metadata.json is invalid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("External task pack metadata.json must be a JSON object.")

    license_value = payload.get("license")
    if not isinstance(license_value, str) or not license_value.strip():
        raise ValueError("External task pack metadata.json must include non-empty `license`.")

    expected = _build_external_expected(payload)
    ok, errors, _report = validate_task_pack_payload(
        root=root,
        payload=payload,
        schema={"type": "object"},
        strict=True,
        return_report=True,
        allowlist_path=None,
        expected_pack=expected,
        allow_unknown_pack=True,
    )
    if not ok:
        preview = "\n".join(f"- {item}" for item in errors[:20])
        remainder = len(errors) - 20
        suffix = f"\n- ... ({remainder} more)" if remainder > 0 else ""
        raise ValueError(f"External task pack failed validation gates:\n{preview}{suffix}")

    pack_hash = compute_external_pack_hash(root)
    pack_name = str(payload.get("pack_name", root.name))

    tasks: list[TaskDefinition] = []
    for item in payload.get("tasks", []):
        if not isinstance(item, dict):
            continue
        task_id = str(item["task_id"])
        rel_path = str(item["path"])
        task_path = (root / rel_path).resolve()
        if not _is_within_root(task_path, root):
            raise ValueError(f"Unsafe external task path for {task_id}: {rel_path}")
        tasks.append(
            TaskDefinition(
                task_id=task_id,
                title=str(item["title"]),
                category=str(item["category"]),
                difficulty=str(item["difficulty"]),
                split=str(item["split"]),
                pack_name=pack_name,
                quick=bool(item.get("quick", False)),
                path=task_path,
            )
        )

    if not tasks:
        raise ValueError("External task pack metadata exists but no tasks were listed.")

    return payload, tasks, pack_hash


def _select_pack_v1(
    *,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
    tasks = load_task_pack_v1()
    selected, selector_source, suite_label = _generic_suite_selection(
        tasks=tasks,
        suite=suite,
        legacy_selector=legacy_selector,
        seed=seed,
    )
    metadata = read_pack_v1_metadata()
    card = _registry_card("task_pack_v1")
    return TaskSelection(
        task_pack="task_pack_v1",
        selector_source=selector_source,
        suite=suite_label,
        tasks=selected,
        pack_version=str(metadata.get("pack_version", "")),
        pack_source="registry" if card else "builtin",
        pack_license=str(card.get("license", "")) if card else None,
        pack_manifest_path=str((Path(__file__).resolve().parent / "task_pack_v1" / "metadata.json")),
    )


def _select_pack_v2(
    *,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
    tasks = load_task_pack_v2()
    selected, selector_source, suite_label = _generic_suite_selection(
        tasks=tasks,
        suite=suite,
        legacy_selector=legacy_selector,
        seed=seed,
    )
    metadata = read_pack_v2_metadata()
    card = _registry_card("task_pack_v2")
    return TaskSelection(
        task_pack="task_pack_v2",
        selector_source=selector_source,
        suite=suite_label,
        tasks=selected,
        pack_version=str(metadata.get("pack_version", "")),
        pack_source="registry" if card else "builtin",
        pack_license=str(card.get("license", "")) if card else None,
        pack_manifest_path=str((Path(__file__).resolve().parent / "task_pack_v2" / "metadata.json")),
    )


def _select_external_pack(
    *,
    task_pack_path: Path,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
    payload, tasks, pack_hash = _load_external_pack(pack_root=task_pack_path)
    selected, selector_source, suite_label = _generic_suite_selection(
        tasks=tasks,
        suite=suite,
        legacy_selector=legacy_selector,
        seed=seed,
    )
    pack_name = str(payload.get("pack_name", task_pack_path.resolve().name))
    pack_version = str(payload.get("pack_version", ""))
    license_value = str(payload.get("license", ""))
    return TaskSelection(
        task_pack=pack_name,
        selector_source=selector_source,
        suite=suite_label,
        tasks=selected,
        pack_version=pack_version,
        pack_source="external",
        pack_license=license_value,
        pack_hash=pack_hash,
        pack_manifest_path=str((task_pack_path.resolve() / "metadata.json")),
    )


def resolve_tasks(
    *,
    task_pack: str,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
    task_pack_path: str | Path | None = None,
) -> TaskSelection:
    if task_pack_path is not None:
        return _select_external_pack(
            task_pack_path=Path(task_pack_path),
            suite=suite,
            legacy_selector=legacy_selector,
            seed=seed,
        )

    normalized_pack = _normalize_task_pack_identifier(task_pack)

    if normalized_pack == "task_pack_v2":
        return _select_pack_v2(suite=suite, legacy_selector=legacy_selector, seed=seed)

    if normalized_pack == "task_pack_v1":
        return _select_pack_v1(suite=suite, legacy_selector=legacy_selector, seed=seed)

    if normalized_pack in {"task_codegen_py", "legacy_codegen_py"}:
        selector = legacy_selector or "all"
        legacy_tasks = select_legacy_tasks(selector)
        selected = _stable_shuffle(legacy_tasks, seed=seed)
        return TaskSelection(
            task_pack="legacy_codegen_py",
            selector_source="tasks",
            suite=selector,
            tasks=selected,
            pack_version="legacy",
            pack_source="legacy",
            pack_license="MIT",
        )

    registry_ids = sorted(
        card_id
        for card in list_pack_cards()
        for card_id in [card.get("pack_id")]
        if isinstance(card_id, str)
    )
    available = ", ".join(sorted(set(registry_ids + ["task_codegen_py", "legacy_codegen_py"])))
    raise ValueError(f"Unknown task pack `{task_pack}`. Available packs: {available}")
