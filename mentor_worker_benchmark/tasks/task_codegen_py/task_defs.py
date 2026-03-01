from __future__ import annotations

from pathlib import Path

from mentor_worker_benchmark.tasks.task_base import TaskDefinition


_TASK_METADATA: list[dict[str, object]] = [
    {"task_id": "bugfix_sum_positive", "title": "Fix sum_positive", "category": "bugfix", "quick": True},
    {"task_id": "bugfix_merge_ranges", "title": "Fix merge_ranges", "category": "bugfix", "quick": False},
    {"task_id": "bugfix_is_palindrome", "title": "Fix is_palindrome", "category": "bugfix", "quick": True},
    {"task_id": "bugfix_dedupe_sorted", "title": "Fix dedupe_sorted", "category": "bugfix", "quick": False},
    {"task_id": "implement_to_snake_case", "title": "Implement to_snake_case", "category": "implement", "quick": False},
    {"task_id": "implement_chunked", "title": "Implement chunked", "category": "implement", "quick": True},
    {"task_id": "implement_top_k_frequent", "title": "Implement top_k_frequent", "category": "implement", "quick": False},
    {"task_id": "implement_balanced_brackets", "title": "Implement balanced_brackets", "category": "implement", "quick": False},
    {"task_id": "refactor_fibonacci", "title": "Refactor fibonacci", "category": "refactor", "quick": False},
    {"task_id": "refactor_flatten", "title": "Refactor flatten", "category": "refactor", "quick": False},
    {"task_id": "refactor_unique_preserve_order", "title": "Refactor unique_preserve_order", "category": "refactor", "quick": True},
    {"task_id": "refactor_parse_query_string", "title": "Refactor parse_query_string", "category": "refactor", "quick": False},
]


def all_tasks() -> list[TaskDefinition]:
    base = Path(__file__).resolve().parent / "task_cases"
    tasks: list[TaskDefinition] = []
    for meta in _TASK_METADATA:
        task_id = str(meta["task_id"])
        tasks.append(
            TaskDefinition(
                task_id=task_id,
                title=str(meta["title"]),
                category=str(meta["category"]),
                path=base / task_id,
                quick=bool(meta.get("quick", False)),
            )
        )
    return tasks


def select_tasks(selector: str) -> list[TaskDefinition]:
    tasks = all_tasks()
    by_id = {task.task_id: task for task in tasks}

    if selector == "all":
        return tasks
    if selector == "quick":
        return [task for task in tasks if task.quick]

    selected: list[TaskDefinition] = []
    for item in [entry.strip() for entry in selector.split(",") if entry.strip()]:
        if item not in by_id:
            known = ", ".join(sorted(by_id))
            raise ValueError(f"Unknown task id `{item}`. Known tasks: {known}")
        selected.append(by_id[item])
    if not selected:
        raise ValueError("No tasks selected.")
    return selected
