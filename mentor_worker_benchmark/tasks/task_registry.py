from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from mentor_worker_benchmark.tasks.task_base import TaskDefinition
from mentor_worker_benchmark.tasks.task_codegen_py.task_defs import select_tasks as select_legacy_tasks
from mentor_worker_benchmark.tasks.task_pack_v1.pack import load_task_pack_v1
from mentor_worker_benchmark.tasks.task_pack_v2.pack import load_task_pack_v2


@dataclass(frozen=True, slots=True)
class TaskSelection:
    task_pack: str
    selector_source: str
    suite: str
    tasks: list[TaskDefinition]


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


def _select_pack_v1(
    *,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
    tasks = load_task_pack_v1()

    if legacy_selector:
        if legacy_selector == "all":
            selected = tasks
            selector_source = "tasks"
            suite_label = "all"
        elif legacy_selector == "quick":
            selected = [task for task in tasks if task.quick]
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
            selected = [task for task in tasks if task.quick]
        else:
            split_tokens = {token.strip() for token in suite_token.split(",") if token.strip()}
            valid = {"train", "dev", "test"}
            if not split_tokens:
                raise ValueError("Suite selector resolved to no splits.")
            if not split_tokens.issubset(valid):
                bad = ", ".join(sorted(split_tokens - valid))
                raise ValueError(f"Unsupported suite token(s): {bad}. Use quick, dev, test, all.")
            selected = [task for task in tasks if task.split in split_tokens]

    if not selected:
        raise ValueError("Task selection produced zero tasks.")

    return TaskSelection(
        task_pack="task_pack_v1",
        selector_source=selector_source,
        suite=suite_label,
        tasks=_stable_shuffle(selected, seed=seed),
    )


def _select_pack_v2(
    *,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
    tasks = load_task_pack_v2()

    def _quick_suite_v2(all_tasks: list[TaskDefinition], *, quick_seed: int) -> list[TaskDefinition]:
        quick_flagged = [task for task in all_tasks if task.quick]
        if quick_flagged:
            ordered = sorted(quick_flagged, key=lambda task: task.task_id)
            return _stable_shuffle(ordered, quick_seed)

        raise ValueError("Quick suite selection found no tasks marked with `quick=true`.")

    if legacy_selector:
        if legacy_selector == "all":
            selected = tasks
            selector_source = "tasks"
            suite_label = "all"
        elif legacy_selector == "quick":
            selected = _quick_suite_v2(tasks, quick_seed=seed)
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
            selected = _quick_suite_v2(tasks, quick_seed=seed)
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
                raise ValueError(f"Unsupported suite token(s): {bad}. Use quick, dev10, dev50, dev, test, all.")
            selected = [task for task in tasks if task.split in split_tokens]

    if not selected:
        raise ValueError("Task selection produced zero tasks.")

    return TaskSelection(
        task_pack="task_pack_v2",
        selector_source=selector_source,
        suite=suite_label,
        tasks=_stable_shuffle(selected, seed=seed),
    )


def resolve_tasks(
    *,
    task_pack: str,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
    if task_pack == "task_pack_v2":
        return _select_pack_v2(suite=suite, legacy_selector=legacy_selector, seed=seed)

    if task_pack == "task_pack_v1":
        return _select_pack_v1(suite=suite, legacy_selector=legacy_selector, seed=seed)

    if task_pack in {"task_codegen_py", "legacy_codegen_py"}:
        selector = legacy_selector or "all"
        legacy_tasks = select_legacy_tasks(selector)
        selected = _stable_shuffle(legacy_tasks, seed=seed)
        return TaskSelection(
            task_pack="legacy_codegen_py",
            selector_source="tasks",
            suite=selector,
            tasks=selected,
        )

    available = ", ".join(["task_pack_v2", "task_pack_v1", "task_codegen_py"])
    raise ValueError(f"Unknown task pack `{task_pack}`. Available packs: {available}")
