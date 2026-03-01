from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from mentor_worker_benchmark.tasks.task_base import TaskDefinition
from mentor_worker_benchmark.tasks.task_codegen_py.task_defs import select_tasks as select_legacy_tasks
from mentor_worker_benchmark.tasks.task_pack_v1.pack import load_task_pack_v1


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


def resolve_tasks(
    *,
    task_pack: str,
    suite: str | None,
    legacy_selector: str | None,
    seed: int,
) -> TaskSelection:
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

    available = ", ".join(["task_pack_v1", "task_codegen_py"])
    raise ValueError(f"Unknown task pack `{task_pack}`. Available packs: {available}")
