from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from mentor_worker_benchmark.tasks.task_base import TaskDefinition


@dataclass(slots=True)
class TestRunResult:
    exit_code: int
    passed: bool
    output: str
    duration_seconds: float
    timed_out: bool = False


def materialize_task(task: TaskDefinition) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temp_dir = tempfile.TemporaryDirectory(prefix=f"mwb_{task.task_id}_")
    workdir = Path(temp_dir.name)
    shutil.copytree(task.path, workdir, dirs_exist_ok=True)
    return temp_dir, workdir


def read_task_prompt(task: TaskDefinition) -> str:
    return (task.path / "prompt.md").read_text(encoding="utf-8")


def project_snapshot(workdir: Path, max_total_chars: int = 24000) -> str:
    tracked_files = sorted(
        p
        for p in workdir.rglob("*")
        if p.is_file() and p.suffix in {".py", ".md", ".txt"} and ".pytest_cache" not in p.parts
    )

    chunks: list[str] = []
    total_chars = 0
    for path in tracked_files:
        rel = path.relative_to(workdir)
        content = path.read_text(encoding="utf-8")
        piece = f"\n# File: {rel}\n{content}\n"
        if total_chars + len(piece) > max_total_chars:
            remaining = max_total_chars - total_chars
            if remaining > 0:
                piece = piece[:remaining]
                chunks.append(piece)
            break
        chunks.append(piece)
        total_chars += len(piece)

    return "".join(chunks).strip()


def run_pytest(workdir: Path, timeout_seconds: int = 20) -> TestRunResult:
    start = time.perf_counter()
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        duration = time.perf_counter() - start
        return TestRunResult(
            exit_code=process.returncode,
            passed=process.returncode == 0,
            output=process.stdout,
            duration_seconds=duration,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - start
        stdout_text = exc.stdout if isinstance(exc.stdout, str) else ""
        return TestRunResult(
            exit_code=124,
            passed=False,
            output=(stdout_text + "\n[timeout] pytest exceeded timeout budget.").strip(),
            duration_seconds=duration,
            timed_out=True,
        )
