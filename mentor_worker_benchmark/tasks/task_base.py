from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TaskDefinition:
    task_id: str
    title: str
    category: str
    path: Path
    split: str = "train"
    difficulty: str = "medium"
    pack_name: str = "legacy_codegen_py"
    quick: bool = False
