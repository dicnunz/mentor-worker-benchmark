from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.tasks.task_base import TaskDefinition


def _pack_dir() -> Path:
    return Path(__file__).resolve().parent


def _metadata_path() -> Path:
    return _pack_dir() / "metadata.json"


@lru_cache(maxsize=1)
def read_pack_metadata() -> dict[str, Any]:
    path = _metadata_path()
    if not path.exists():
        raise RuntimeError(
            "task_pack_v1 metadata.json is missing. Generate it with "
            "`python -m mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack --seed 1337`."
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_task_pack_v1() -> list[TaskDefinition]:
    payload = read_pack_metadata()
    base = _pack_dir()

    tasks: list[TaskDefinition] = []
    for item in payload.get("tasks", []):
        task_id = str(item["task_id"])
        rel_path = str(item["path"])
        tasks.append(
            TaskDefinition(
                task_id=task_id,
                title=str(item["title"]),
                category=str(item["category"]),
                difficulty=str(item["difficulty"]),
                split=str(item["split"]),
                pack_name="task_pack_v1",
                quick=bool(item.get("quick", False)),
                path=(base / rel_path).resolve(),
            )
        )

    if not tasks:
        raise RuntimeError("task_pack_v1 metadata exists but no tasks were listed.")
    return tasks
