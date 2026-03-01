from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

TaskCategory = Literal["bugfix", "implement", "refactor"]


@dataclass(frozen=True, slots=True)
class TaskDefinition:
    task_id: str
    title: str
    category: TaskCategory
    path: Path
    quick: bool = False
