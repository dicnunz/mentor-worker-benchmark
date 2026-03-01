from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.tasks.task_codegen_py.harness import (
    materialize_task,
    project_snapshot,
    read_task_prompt,
    run_pytest,
)
from mentor_worker_benchmark.tasks.task_codegen_py.task_defs import select_tasks

DEFAULT_MODELS = [
    "llama3.1:8b",
    "qwen2.5-coder:7b",
    "mistral:7b",
    "phi3:mini",
    "gemma2:9b",
]

WORKER_SYSTEM_PROMPT = (
    "You are a precise coding agent. Return only valid unified diff patches unless explicitly asked otherwise."
)

MENTOR_SYSTEM_PROMPT = (
    "You are a software mentor. You are forbidden from writing code snippets, full file content, or diff patches. "
    "Provide only high-level natural language guidance."
)

DIFF_BLOCK_RE = re.compile(r"```(?:diff)?\n(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass(slots=True)
class BenchmarkConfig:
    models: list[str]
    max_turns: int = 4
    task_selector: str = "all"
    results_path: Path = Path("results/results.json")


def _estimate_tokens(text: str) -> int:
    # Rough local estimate for cross-model comparability.
    return max(1, len(text) // 4)


def _load_template(name: str) -> str:
    template_path = (
        Path(__file__).resolve().parent
        / "tasks"
        / "task_codegen_py"
        / "templates"
        / name
    )
    return template_path.read_text(encoding="utf-8")


def _extract_diff(text: str) -> str | None:
    text = text.strip()
    blocks = [block.strip() for block in DIFF_BLOCK_RE.findall(text)]
    candidates = blocks + [text]

    for candidate in candidates:
        if "--- " in candidate and "+++ " in candidate:
            return f"{candidate}\n"
        if "diff --git" in candidate:
            return f"{candidate}\n"
    return None


def _apply_patch(workdir: Path, diff_text: str) -> tuple[bool, str]:
    attempts = [
        ["patch", "-p0", "--batch", "--forward"],
        ["patch", "-p1", "--batch", "--forward"],
    ]

    logs: list[str] = []
    for command in attempts:
        process = subprocess.run(
            command,
            cwd=workdir,
            input=diff_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        logs.append(f"$ {' '.join(command)}\n{process.stdout}")
        if process.returncode == 0:
            return True, "\n".join(logs)

    return False, "\n".join(logs)


def _is_mentor_violation(text: str) -> bool:
    if "```" in text:
        return True

    bad_patterns = [
        r"^diff --git",
        r"^--- ",
        r"^\+\+\+ ",
        r"^@@",
        r"^\+\s*\w",
        r"^\s*(def|class|import|from)\s+",
    ]
    for pattern in bad_patterns:
        if re.search(pattern, text, flags=re.MULTILINE):
            return True
    return False


def _sanitize_mentor_guidance(text: str) -> tuple[str, bool]:
    violation = _is_mentor_violation(text)
    if not violation:
        return text.strip(), False

    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    cleaned_lines: list[str] = []
    for line in without_fences.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("diff --git", "---", "+++", "@@", "+", "-")):
            continue
        if re.match(r"^(def|class|import|from)\s+", stripped):
            continue
        cleaned_lines.append(stripped)

    guidance = " ".join(cleaned_lines).strip()
    if not guidance:
        guidance = "Read the failing assertions carefully and make the smallest targeted fix needed to satisfy tests."
    return guidance, True


def _render_worker_prompt(
    *,
    template: str,
    task_prompt: str,
    snapshot: str,
    failure_output: str,
    mentor_guidance: str,
) -> str:
    return template.format(
        task_prompt=task_prompt.strip(),
        snapshot=snapshot.strip() or "(snapshot unavailable)",
        failure_output=failure_output.strip() or "(not available)",
        mentor_guidance=mentor_guidance.strip() or "(none)",
    )


def _render_mentor_prompt(
    *,
    template: str,
    task_prompt: str,
    worker_patch: str,
    failure_output: str,
) -> str:
    return template.format(
        task_prompt=task_prompt.strip(),
        worker_patch=worker_patch.strip() or "(worker did not provide a valid patch)",
        failure_output=failure_output.strip() or "(not available)",
    )


def _baseline_run(
    client: OllamaClient,
    worker_model: str,
    task_prompt: str,
    task_id: str,
    worker_template: str,
    workdir: Path,
) -> dict[str, Any]:
    start = time.perf_counter()
    initial_tests = run_pytest(workdir)
    snapshot = project_snapshot(workdir)
    worker_prompt = _render_worker_prompt(
        template=worker_template,
        task_prompt=task_prompt,
        snapshot=snapshot,
        failure_output=initial_tests.output,
        mentor_guidance="(none)",
    )

    worker_response = client.chat(
        model=worker_model,
        messages=[{"role": "user", "content": worker_prompt}],
        system=WORKER_SYSTEM_PROMPT,
        temperature=0.0,
        top_p=1.0,
    )
    extracted = _extract_diff(worker_response)
    patch_applied = False
    patch_log = "No valid unified diff found in worker response."
    if extracted:
        patch_applied, patch_log = _apply_patch(workdir, extracted)

    final_tests = run_pytest(workdir)
    elapsed = time.perf_counter() - start

    total_tokens = (
        _estimate_tokens(worker_prompt)
        + _estimate_tokens(worker_response)
        + _estimate_tokens(initial_tests.output)
        + _estimate_tokens(final_tests.output)
    )

    return {
        "mode": "baseline",
        "task_id": task_id,
        "worker_model": worker_model,
        "mentor_model": None,
        "pass": final_tests.passed,
        "turns_used": 1,
        "wall_time_seconds": round(elapsed, 4),
        "total_tokens_estimate": total_tokens,
        "log": {
            "initial_test_output": initial_tests.output,
            "worker_prompt": worker_prompt,
            "worker_response": worker_response,
            "extracted_patch": extracted,
            "patch_applied": patch_applied,
            "patch_log": patch_log,
            "final_test_output": final_tests.output,
        },
    }


def _mentored_run(
    client: OllamaClient,
    mentor_model: str,
    worker_model: str,
    task_prompt: str,
    task_id: str,
    worker_template: str,
    mentor_template: str,
    workdir: Path,
    max_turns: int,
) -> dict[str, Any]:
    start = time.perf_counter()
    guidance_history: list[str] = []
    turns: list[dict[str, Any]] = []

    current_tests = run_pytest(workdir)
    token_accumulator = _estimate_tokens(current_tests.output)
    passed = current_tests.passed

    for turn_index in range(1, max_turns + 1):
        snapshot = project_snapshot(workdir)
        worker_prompt = _render_worker_prompt(
            template=worker_template,
            task_prompt=task_prompt,
            snapshot=snapshot,
            failure_output=current_tests.output,
            mentor_guidance="\n".join(guidance_history[-3:]),
        )

        worker_response = client.chat(
            model=worker_model,
            messages=[{"role": "user", "content": worker_prompt}],
            system=WORKER_SYSTEM_PROMPT,
            temperature=0.0,
            top_p=1.0,
        )

        token_accumulator += _estimate_tokens(worker_prompt) + _estimate_tokens(worker_response)
        extracted = _extract_diff(worker_response)
        patch_applied = False
        patch_log = "No valid unified diff found in worker response."
        if extracted:
            patch_applied, patch_log = _apply_patch(workdir, extracted)

        current_tests = run_pytest(workdir)
        token_accumulator += _estimate_tokens(current_tests.output)
        passed = current_tests.passed

        turn_log: dict[str, Any] = {
            "turn": turn_index,
            "worker_prompt": worker_prompt,
            "worker_response": worker_response,
            "extracted_patch": extracted,
            "patch_applied": patch_applied,
            "patch_log": patch_log,
            "test_output": current_tests.output,
            "pass_after_turn": passed,
        }

        if passed:
            turns.append(turn_log)
            break

        if turn_index < max_turns:
            mentor_prompt = _render_mentor_prompt(
                template=mentor_template,
                task_prompt=task_prompt,
                worker_patch=worker_response,
                failure_output=current_tests.output,
            )

            mentor_response = client.chat(
                model=mentor_model,
                messages=[{"role": "user", "content": mentor_prompt}],
                system=MENTOR_SYSTEM_PROMPT,
                temperature=0.0,
                top_p=1.0,
            )
            mentor_guidance, violation = _sanitize_mentor_guidance(mentor_response)
            guidance_history.append(mentor_guidance)
            token_accumulator += _estimate_tokens(mentor_prompt) + _estimate_tokens(mentor_response)

            turn_log["mentor_prompt"] = mentor_prompt
            turn_log["mentor_response_raw"] = mentor_response
            turn_log["mentor_guidance"] = mentor_guidance
            turn_log["mentor_violation"] = violation

        turns.append(turn_log)

    elapsed = time.perf_counter() - start
    return {
        "mode": "mentored",
        "task_id": task_id,
        "worker_model": worker_model,
        "mentor_model": mentor_model,
        "pass": passed,
        "turns_used": len(turns),
        "wall_time_seconds": round(elapsed, 4),
        "total_tokens_estimate": token_accumulator,
        "log": {
            "task_prompt": task_prompt,
            "turns": turns,
        },
    }


def _compute_aggregates(
    runs: list[dict[str, Any]], models: list[str], task_ids: list[str]
) -> dict[str, Any]:
    baseline_runs = [run for run in runs if run["mode"] == "baseline"]
    mentored_runs = [run for run in runs if run["mode"] == "mentored"]

    baseline_by_worker: dict[str, float] = {}
    for worker in models:
        worker_baselines = [run for run in baseline_runs if run["worker_model"] == worker]
        if worker_baselines:
            baseline_by_worker[worker] = mean(1.0 if run["pass"] else 0.0 for run in worker_baselines)
        else:
            baseline_by_worker[worker] = 0.0

    mentor_worker_pairs: list[dict[str, Any]] = []
    for mentor in models:
        for worker in models:
            pair_runs = [
                run
                for run in mentored_runs
                if run["mentor_model"] == mentor and run["worker_model"] == worker
            ]
            pass_rate = mean(1.0 if run["pass"] else 0.0 for run in pair_runs) if pair_runs else 0.0
            baseline_rate = baseline_by_worker[worker]
            mentor_worker_pairs.append(
                {
                    "mentor_model": mentor,
                    "worker_model": worker,
                    "mentored_pass_rate": round(pass_rate, 4),
                    "baseline_pass_rate": round(baseline_rate, 4),
                    "mentorship_lift": round(pass_rate - baseline_rate, 4),
                }
            )

    mentor_rankings: list[dict[str, Any]] = []
    for mentor in models:
        mentor_pairs = [row for row in mentor_worker_pairs if row["mentor_model"] == mentor]
        mentor_runs = [row for row in mentored_runs if row["mentor_model"] == mentor]
        avg_lift = mean(row["mentorship_lift"] for row in mentor_pairs) if mentor_pairs else 0.0
        pass_rate = mean(1.0 if row["pass"] else 0.0 for row in mentor_runs) if mentor_runs else 0.0
        mentor_rankings.append(
            {
                "mentor_model": mentor,
                "avg_lift_across_workers": round(avg_lift, 4),
                "overall_mentored_pass_rate": round(pass_rate, 4),
            }
        )

    mentor_rankings.sort(
        key=lambda row: (row["avg_lift_across_workers"], row["overall_mentored_pass_rate"]),
        reverse=True,
    )

    worker_rankings: list[dict[str, Any]] = []
    for worker in models:
        worker_mentored = [run for run in mentored_runs if run["worker_model"] == worker]
        mentored_rate = mean(1.0 if run["pass"] else 0.0 for run in worker_mentored) if worker_mentored else 0.0
        worker_rankings.append(
            {
                "worker_model": worker,
                "baseline_pass_rate": round(baseline_by_worker[worker], 4),
                "mentored_pass_rate": round(mentored_rate, 4),
                "delta": round(mentored_rate - baseline_by_worker[worker], 4),
            }
        )

    worker_rankings.sort(key=lambda row: (row["mentored_pass_rate"], row["baseline_pass_rate"]), reverse=True)

    return {
        "task_count": len(task_ids),
        "tasks": task_ids,
        "baseline_by_worker": baseline_by_worker,
        "mentor_worker_pairs": mentor_worker_pairs,
        "best_mentors": mentor_rankings,
        "best_workers": worker_rankings,
    }


def _to_markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(title for _, title in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]) for key, _ in columns) + " |")
    return "\n".join(lines)


def write_leaderboard(results: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    aggregates = results["aggregates"]
    mentors = aggregates["best_mentors"]
    workers = aggregates["best_workers"]
    pairs = aggregates["mentor_worker_pairs"]

    top_line = "No runs completed."
    if mentors:
        top = mentors[0]
        top_line = (
            f"Top mentor: `{top['mentor_model']}` with average lift {top['avg_lift_across_workers']:.2%} "
            f"and mentored pass rate {top['overall_mentored_pass_rate']:.2%}."
        )

    mentor_table = _to_markdown_table(
        mentors,
        [
            ("mentor_model", "Mentor"),
            ("avg_lift_across_workers", "Avg Lift"),
            ("overall_mentored_pass_rate", "Mentored Pass Rate"),
        ],
    )
    worker_table = _to_markdown_table(
        workers,
        [
            ("worker_model", "Worker"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("delta", "Delta"),
        ],
    )
    pair_table = _to_markdown_table(
        pairs,
        [
            ("mentor_model", "Mentor"),
            ("worker_model", "Worker"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("mentorship_lift", "Lift"),
        ],
    )

    content = f"""# Mentor-Worker Benchmark Leaderboard

Generated: {results['generated_at']}

{top_line}

## Best Mentors
{mentor_table}

## Best Workers
{worker_table}

## Mentor + Worker Pairs
{pair_table}
"""
    output_path.write_text(content, encoding="utf-8")


def run_benchmark(config: BenchmarkConfig, client: OllamaClient | None = None) -> dict[str, Any]:
    client = client or OllamaClient()

    selected_tasks = select_tasks(config.task_selector)
    worker_template = _load_template("worker_prompt.txt")
    mentor_template = _load_template("mentor_prompt.txt")

    runs: list[dict[str, Any]] = []
    baseline_lookup: dict[tuple[str, str], bool] = {}

    benchmark_start = time.perf_counter()

    for worker_model in config.models:
        for task in selected_tasks:
            temp_dir, workdir = materialize_task(task)
            try:
                task_prompt = read_task_prompt(task)
                baseline = _baseline_run(
                    client=client,
                    worker_model=worker_model,
                    task_prompt=task_prompt,
                    task_id=task.task_id,
                    worker_template=worker_template,
                    workdir=workdir,
                )
                runs.append(baseline)
                baseline_lookup[(worker_model, task.task_id)] = bool(baseline["pass"])
            finally:
                temp_dir.cleanup()

    for mentor_model in config.models:
        for worker_model in config.models:
            for task in selected_tasks:
                temp_dir, workdir = materialize_task(task)
                try:
                    task_prompt = read_task_prompt(task)
                    mentored = _mentored_run(
                        client=client,
                        mentor_model=mentor_model,
                        worker_model=worker_model,
                        task_prompt=task_prompt,
                        task_id=task.task_id,
                        worker_template=worker_template,
                        mentor_template=mentor_template,
                        workdir=workdir,
                        max_turns=config.max_turns,
                    )
                    mentored["baseline_pass"] = baseline_lookup[(worker_model, task.task_id)]
                    mentored["mentorship_lift"] = int(bool(mentored["pass"])) - int(
                        bool(mentored["baseline_pass"])
                    )
                    runs.append(mentored)
                finally:
                    temp_dir.cleanup()

    elapsed = time.perf_counter() - benchmark_start

    task_ids = [task.task_id for task in selected_tasks]
    aggregates = _compute_aggregates(runs, models=config.models, task_ids=task_ids)
    results = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "config": {
            "models": config.models,
            "max_turns": config.max_turns,
            "task_selector": config.task_selector,
            "task_count": len(task_ids),
        },
        "summary": {
            "total_runs": len(runs),
            "benchmark_wall_time_seconds": round(elapsed, 4),
        },
        "runs": runs,
        "aggregates": aggregates,
    }

    config.results_path.parent.mkdir(parents=True, exist_ok=True)
    config.results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_leaderboard(results, config.results_path.parent / "leaderboard.md")
    return results
