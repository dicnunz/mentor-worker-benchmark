from __future__ import annotations

import os
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
        if p.is_file()
        and p.suffix in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".ini", ".cfg"}
        and ".pytest_cache" not in p.parts
        and "__pycache__" not in p.parts
    )

    def _priority(path: Path) -> tuple[int, str]:
        rel = path.relative_to(workdir).as_posix()
        if rel.startswith("tests/"):
            return (0, rel)
        if rel.startswith("src/"):
            return (1, rel)
        if rel.startswith("tools/"):
            return (2, rel)
        if rel.startswith("data/"):
            return (3, rel)
        if rel in {"prompt.md", "README.md"}:
            return (4, rel)
        return (5, rel)

    tree_lines = ["## File Tree"]
    for path in tracked_files[:180]:
        tree_lines.append(f"- {path.relative_to(workdir).as_posix()}")
    if len(tracked_files) > 180:
        tree_lines.append(f"- ... ({len(tracked_files) - 180} more files)")

    blocks: list[str] = ["\n".join(tree_lines), "", "## Relevant File Excerpts"]
    current = "\n".join(blocks)
    remaining = max_total_chars - len(current)
    if remaining <= 0:
        return current[:max_total_chars]

    for path in sorted(tracked_files, key=_priority):
        rel = path.relative_to(workdir).as_posix()
        content = path.read_text(encoding="utf-8")
        excerpt_limit = 1200 if rel.startswith(("tests/", "src/")) else 700
        excerpt = content[:excerpt_limit]
        if len(content) > excerpt_limit:
            excerpt += "\n...<truncated>"

        section = f"\n### {rel}\n{excerpt}\n"
        if len(section) > remaining:
            if remaining > 80:
                blocks.append(section[:remaining] + "\n...<snapshot-truncated>")
            break
        blocks.append(section)
        remaining -= len(section)

    return "\n".join(blocks).strip()


def run_pytest(workdir: Path, timeout_seconds: int = 8) -> TestRunResult:
    start = time.perf_counter()
    runtime_hook_dir = Path(__file__).resolve().parents[2] / "_runtime"
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{runtime_hook_dir}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(runtime_hook_dir)
    )
    env["MWB_BLOCK_NETWORK"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    try:
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=workdir,
            env=env,
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
