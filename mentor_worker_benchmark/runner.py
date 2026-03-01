from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from mentor_worker_benchmark import __version__
from mentor_worker_benchmark.llm_client import LLMClient
from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.tasks.task_codegen_py.harness import (
    materialize_task,
    project_snapshot,
    read_task_prompt,
    run_pytest,
)
from mentor_worker_benchmark.tasks.task_registry import resolve_tasks

DEFAULT_MODELS = [
    "llama3.1:8b",
    "qwen2.5-coder:7b",
    "mistral:7b",
    "phi3:mini",
    "gemma2:9b",
]

DEFAULT_RUN_MODES = (
    "worker_only",
    "mentor_worker",
    "mentor_only_suggestion_noise",
)

VALID_RUN_MODES = {
    "worker_only",
    "mentor_worker",
    "mentor_only_suggestion_noise",
    "stronger_worker",
    "mentor_swap",
}

REPRO_MAX_TURNS = 2
REPRO_WORKER_MAX_TOKENS = 640
REPRO_MENTOR_MAX_TOKENS = 220
REPRO_TEMPERATURE = 0.0
REPRO_TOP_P = 1.0

WORKER_SYSTEM_PROMPT = (
    "You are a precise coding agent. Return only a valid unified diff patch and nothing else."
)

MENTOR_SYSTEM_PROMPT = (
    "You are a software mentor. You are forbidden from writing code snippets, full file content, or diff patches. "
    "Provide only concise high-level natural-language guidance."
)

MENTOR_SAFE_SUMMARY = (
    "Focus on the failing assertions and propose one small strategy: identify the likely bug source, "
    "apply the minimal change, and re-run tests."
)

DIFF_BLOCK_RE = re.compile(r"```(?:diff)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
FENCED_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)
IMPORT_RE = re.compile(r"^\s*(import|from)\s+[A-Za-z0-9_.]+", re.MULTILINE)
FUNCTION_DEF_RE = re.compile(r"^\s*def\s+[A-Za-z0-9_]+\s*\(", re.MULTILINE)
CLASS_DEF_RE = re.compile(r"^\s*class\s+[A-Za-z0-9_]+\s*[:(]", re.MULTILINE)
DIFF_MARKER_RE = re.compile(r"^(diff --git|---\s|\+\+\+\s|@@)", re.MULTILINE)
FILE_HEADER_RE = re.compile(r"^\s*#\s*File:\s+", re.MULTILINE)
MENTOR_CODE_BLOCK_MAX_LINES = 8


@dataclass(slots=True)
class BenchmarkConfig:
    models: list[str]
    mentor_models_override: list[str] | None = None
    worker_models_override: list[str] | None = None
    provider: str = "ollama"
    mentor_provider: str | None = None
    worker_provider: str | None = None
    max_turns: int = 4
    task_pack: str = "task_pack_v1"
    suite: str | None = None
    task_selector: str | None = None
    seed: int = 1337
    results_path: Path = Path("results/results.json")
    run_modes: tuple[str, ...] = DEFAULT_RUN_MODES
    repro_mode: bool = False
    stronger_worker_model: str | None = None
    worker_num_predict_override: int | None = None
    mentor_num_predict_override: int | None = None


@dataclass(slots=True)
class GenerationSettings:
    temperature: float
    top_p: float
    worker_num_predict: int
    mentor_num_predict: int
    max_turns: int
    seed: int


@dataclass(slots=True)
class MentorValidation:
    guidance: str
    violated: bool
    reasons: list[str]
    original: str | None


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


def _normalize_run_modes(run_modes: tuple[str, ...] | list[str]) -> list[str]:
    ordered: list[str] = []
    for mode in run_modes:
        mode_normalized = mode.strip()
        if not mode_normalized:
            continue
        if mode_normalized not in VALID_RUN_MODES:
            known = ", ".join(sorted(VALID_RUN_MODES))
            raise ValueError(f"Unknown run mode `{mode_normalized}`. Allowed values: {known}")
        if mode_normalized not in ordered:
            ordered.append(mode_normalized)

    if not ordered:
        raise ValueError("No run modes selected.")
    return ordered


def _seed_for_call(base_seed: int, *parts: str) -> int:
    joined = "|".join(parts)
    digest = hashlib.sha256(f"{base_seed}|{joined}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _normalize_patch_path(raw_path: str) -> str | None:
    token = raw_path.split("\t", 1)[0].strip()
    if token == "/dev/null":
        return None
    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]
    return token


def _validate_patch_format(diff_text: str) -> tuple[bool, str]:
    if "--- " not in diff_text or "+++ " not in diff_text:
        return False, "Patch missing unified diff file headers (`---`/`+++`)."
    if "@@" not in diff_text:
        return False, "Patch missing hunk markers (`@@`)."

    checked_paths = 0
    for line in diff_text.splitlines():
        if not line.startswith(("--- ", "+++ ")):
            continue
        normalized = _normalize_patch_path(line[4:])
        if not normalized:
            continue

        checked_paths += 1
        candidate = Path(normalized)
        if candidate.is_absolute() or normalized.startswith("~"):
            return False, f"Unsafe patch path `{normalized}` (absolute/home path)."
        if any(part == ".." for part in candidate.parts):
            return False, f"Unsafe patch path `{normalized}` (path traversal)."

    if checked_paths == 0:
        return False, "Patch did not reference any project file paths."

    return True, "ok"


def _extract_diff(text: str) -> str | None:
    text = text.strip()
    blocks = [block.strip() for block in DIFF_BLOCK_RE.findall(text)]
    candidates = blocks + [text]

    for candidate in candidates:
        valid, _ = _validate_patch_format(candidate)
        if valid:
            return f"{candidate}\n"
    return None


def _apply_patch(workdir: Path, diff_text: str) -> tuple[bool, str]:
    valid, reason = _validate_patch_format(diff_text)
    if not valid:
        return False, reason

    attempts = [
        ["patch", "-p0", "--batch", "--forward", "--reject-file=-"],
        ["patch", "-p1", "--batch", "--forward", "--reject-file=-"],
    ]

    logs: list[str] = []
    for command in attempts:
        try:
            process = subprocess.run(
                command,
                cwd=workdir,
                input=diff_text,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=12,
            )
            logs.append(f"$ {' '.join(command)}\n{process.stdout}")
            if process.returncode == 0:
                return True, "\n".join(logs)
        except subprocess.TimeoutExpired:
            logs.append(f"$ {' '.join(command)}\n[timeout] patch command timed out")

    return False, "\n".join(logs)


def _detect_mentor_violation_reasons(text: str) -> list[str]:
    reasons: set[str] = set()

    fenced_blocks = FENCED_BLOCK_RE.findall(text)
    if fenced_blocks:
        reasons.add("code_block")
        for block in fenced_blocks:
            line_count = len([line for line in block.splitlines() if line.strip()])
            if line_count > MENTOR_CODE_BLOCK_MAX_LINES:
                reasons.add("long_code_block")

    if DIFF_MARKER_RE.search(text):
        reasons.add("diff_syntax")
    if FILE_HEADER_RE.search(text):
        reasons.add("file_header")
    if IMPORT_RE.search(text):
        reasons.add("import_statement")
    if FUNCTION_DEF_RE.search(text):
        reasons.add("function_definition")
    if CLASS_DEF_RE.search(text):
        reasons.add("class_definition")

    return sorted(reasons)


def _summarize_guidance_text(raw_text: str) -> str:
    cleaned_lines: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("diff --git", "---", "+++", "@@", "+", "-", "# File:")):
            continue
        if IMPORT_RE.match(stripped) or FUNCTION_DEF_RE.match(stripped) or CLASS_DEF_RE.match(stripped):
            continue
        if stripped.startswith("```"):
            continue
        cleaned_lines.append(stripped)

    guidance = " ".join(cleaned_lines)
    guidance = re.sub(r"\s+", " ", guidance).strip()

    if len(guidance.split()) < 8:
        return MENTOR_SAFE_SUMMARY
    if len(guidance) > 320:
        guidance = guidance[:320].rsplit(" ", 1)[0].strip() + "."
    return guidance


def _validate_mentor_output(text: str) -> MentorValidation:
    reasons = _detect_mentor_violation_reasons(text)
    if not reasons:
        guidance = re.sub(r"\s+", " ", text).strip()
        return MentorValidation(guidance=guidance or MENTOR_SAFE_SUMMARY, violated=False, reasons=[], original=None)

    summary = _summarize_guidance_text(text)
    return MentorValidation(
        guidance=summary,
        violated=True,
        reasons=reasons,
        original=text,
    )


def _sanitize_mentor_guidance(text: str) -> tuple[str, bool]:
    validation = _validate_mentor_output(text)
    return validation.guidance, validation.violated


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


def _dummy_mentor_guidance(turn_index: int) -> str:
    advice = [
        "Start by reading failing assertion messages and target only one bug source.",
        "Prefer minimal edits and keep function signatures unchanged.",
        "After patching, verify edge cases mentioned by tests.",
        "If a patch fails, simplify and focus on deterministic behavior.",
    ]
    return advice[(turn_index - 1) % len(advice)]


def _baseline_run(
    client: LLMClient,
    worker_model: str,
    task_prompt: str,
    task_id: str,
    worker_template: str,
    workdir: Path,
    generation: GenerationSettings,
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

    worker_seed = _seed_for_call(generation.seed, "worker_only", worker_model, task_id)
    worker_error: str | None = None
    try:
        worker_response = client.chat(
            model=worker_model,
            messages=[{"role": "user", "content": worker_prompt}],
            system=WORKER_SYSTEM_PROMPT,
            temperature=generation.temperature,
            top_p=generation.top_p,
            num_predict=generation.worker_num_predict,
            seed=worker_seed,
        )
    except RuntimeError as exc:
        worker_response = f"[worker_error] {exc}"
        worker_error = str(exc)

    extracted = _extract_diff(worker_response)
    patch_applied = False
    patch_log = "No valid unified diff found in worker response."
    if extracted:
        patch_applied, patch_log = _apply_patch(workdir, extracted)
    elif worker_error:
        patch_log = worker_error

    final_tests = run_pytest(workdir)
    elapsed = time.perf_counter() - start

    total_tokens = (
        _estimate_tokens(worker_prompt)
        + _estimate_tokens(worker_response)
        + _estimate_tokens(initial_tests.output)
        + _estimate_tokens(final_tests.output)
    )

    return {
        "mode": "worker_only",
        "task_id": task_id,
        "worker_model": worker_model,
        "mentor_model": None,
        "pass": final_tests.passed,
        "turns_used": 1,
        "wall_time_seconds": round(elapsed, 4),
        "total_tokens_estimate": total_tokens,
        "mentor_turn_count": 0,
        "mentor_violation_count": 0,
        "log": {
            "initial_test_output": initial_tests.output,
            "worker_prompt": worker_prompt,
            "worker_response": worker_response,
            "worker_error": worker_error,
            "extracted_patch": extracted,
            "patch_applied": patch_applied,
            "patch_log": patch_log,
            "final_test_output": final_tests.output,
        },
    }


def _mentored_run(
    worker_client: LLMClient,
    mentor_client: LLMClient,
    mentor_model: str,
    worker_model: str,
    task_prompt: str,
    task_id: str,
    worker_template: str,
    mentor_template: str,
    workdir: Path,
    generation: GenerationSettings,
    mentor_strategy: Literal["real", "dummy_control"] = "real",
) -> dict[str, Any]:
    start = time.perf_counter()
    guidance_history: list[str] = []
    turns: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    current_tests = run_pytest(workdir)
    token_accumulator = _estimate_tokens(current_tests.output)
    passed = current_tests.passed

    for turn_index in range(1, generation.max_turns + 1):
        snapshot = project_snapshot(workdir)
        worker_prompt = _render_worker_prompt(
            template=worker_template,
            task_prompt=task_prompt,
            snapshot=snapshot,
            failure_output=current_tests.output,
            mentor_guidance="\n".join(guidance_history[-3:]),
        )

        worker_seed = _seed_for_call(
            generation.seed,
            mentor_strategy,
            mentor_model,
            worker_model,
            task_id,
            f"worker_turn_{turn_index}",
        )
        worker_error: str | None = None
        try:
            worker_response = worker_client.chat(
                model=worker_model,
                messages=[{"role": "user", "content": worker_prompt}],
                system=WORKER_SYSTEM_PROMPT,
                temperature=generation.temperature,
                top_p=generation.top_p,
                num_predict=generation.worker_num_predict,
                seed=worker_seed,
            )
        except RuntimeError as exc:
            worker_response = f"[worker_error] {exc}"
            worker_error = str(exc)

        token_accumulator += _estimate_tokens(worker_prompt) + _estimate_tokens(worker_response)
        extracted = _extract_diff(worker_response)
        patch_applied = False
        patch_log = "No valid unified diff found in worker response."
        if extracted:
            patch_applied, patch_log = _apply_patch(workdir, extracted)
        elif worker_error:
            patch_log = worker_error

        current_tests = run_pytest(workdir)
        token_accumulator += _estimate_tokens(current_tests.output)
        passed = current_tests.passed

        turn_log: dict[str, Any] = {
            "turn": turn_index,
            "worker_prompt": worker_prompt,
            "worker_response": worker_response,
            "worker_error": worker_error,
            "extracted_patch": extracted,
            "patch_applied": patch_applied,
            "patch_log": patch_log,
            "test_output": current_tests.output,
            "pass_after_turn": passed,
        }

        if passed:
            turns.append(turn_log)
            break

        if turn_index < generation.max_turns:
            mentor_prompt = _render_mentor_prompt(
                template=mentor_template,
                task_prompt=task_prompt,
                worker_patch=worker_response,
                failure_output=current_tests.output,
            )

            mentor_error: str | None = None
            validation: MentorValidation
            if mentor_strategy == "dummy_control":
                mentor_response = _dummy_mentor_guidance(turn_index)
                validation = MentorValidation(
                    guidance=mentor_response,
                    violated=False,
                    reasons=[],
                    original=None,
                )
            else:
                mentor_seed = _seed_for_call(
                    generation.seed,
                    mentor_strategy,
                    mentor_model,
                    worker_model,
                    task_id,
                    f"mentor_turn_{turn_index}",
                )
                try:
                    mentor_response = mentor_client.chat(
                        model=mentor_model,
                        messages=[{"role": "user", "content": mentor_prompt}],
                        system=MENTOR_SYSTEM_PROMPT,
                        temperature=generation.temperature,
                        top_p=generation.top_p,
                        num_predict=generation.mentor_num_predict,
                        seed=mentor_seed,
                    )
                except RuntimeError as exc:
                    mentor_response = f"[mentor_error] {exc}"
                    mentor_error = str(exc)

                validation = _validate_mentor_output(mentor_response)
                if mentor_error:
                    validation = MentorValidation(
                        guidance=MENTOR_SAFE_SUMMARY,
                        violated=False,
                        reasons=["mentor_request_error"],
                        original=None,
                    )

            guidance_history.append(validation.guidance)
            token_accumulator += _estimate_tokens(mentor_prompt) + _estimate_tokens(validation.guidance)

            turn_log["mentor_prompt"] = mentor_prompt
            turn_log["mentor_response_raw"] = mentor_response if mentor_strategy == "real" else None
            turn_log["mentor_error"] = mentor_error
            turn_log["mentor_guidance"] = validation.guidance
            turn_log["mentor_violation"] = validation.violated
            turn_log["mentor_violation_reasons"] = validation.reasons

            if validation.violated:
                violations.append(
                    {
                        "turn": turn_index,
                        "mentor_model": mentor_model,
                        "reasons": validation.reasons,
                        "original": validation.original,
                        "replacement_guidance": validation.guidance,
                    }
                )

        turns.append(turn_log)

    elapsed = time.perf_counter() - start
    mode_name = "mentor_worker" if mentor_strategy == "real" else "mentor_only_suggestion_noise"
    mentor_turn_count = sum(1 for turn in turns if "mentor_prompt" in turn)

    return {
        "mode": mode_name,
        "task_id": task_id,
        "worker_model": worker_model,
        "mentor_model": mentor_model,
        "pass": passed,
        "turns_used": len(turns),
        "wall_time_seconds": round(elapsed, 4),
        "total_tokens_estimate": token_accumulator,
        "mentor_turn_count": mentor_turn_count,
        "mentor_violation_count": len(violations),
        "log": {
            "task_prompt": task_prompt,
            "turns": turns,
            "violations": violations,
        },
    }


def _rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return mean(1.0 if row.get("pass") else 0.0 for row in rows)


def _compute_aggregates(
    *,
    runs: list[dict[str, Any]],
    worker_models: list[str],
    mentor_models: list[str],
    task_categories: dict[str, str],
) -> dict[str, Any]:
    worker_only_runs = [run for run in runs if run["mode"] == "worker_only"]
    mentor_worker_runs = [run for run in runs if run["mode"] == "mentor_worker"]
    control_runs = [run for run in runs if run["mode"] == "mentor_only_suggestion_noise"]

    baseline_by_worker = {
        worker: _rate([row for row in worker_only_runs if row["worker_model"] == worker])
        for worker in worker_models
    }
    control_by_worker = {
        worker: _rate([row for row in control_runs if row["worker_model"] == worker])
        for worker in worker_models
    }

    mentor_worker_pairs: list[dict[str, Any]] = []
    for mentor in mentor_models:
        for worker in worker_models:
            pair_runs = [
                run
                for run in mentor_worker_runs
                if run["mentor_model"] == mentor and run["worker_model"] == worker
            ]
            pass_rate = _rate(pair_runs)
            violation_turns = sum(int(run.get("mentor_turn_count", 0)) for run in pair_runs)
            violation_count = sum(int(run.get("mentor_violation_count", 0)) for run in pair_runs)
            violation_rate = (violation_count / violation_turns) if violation_turns else 0.0
            baseline_rate = baseline_by_worker.get(worker, 0.0)
            control_rate = control_by_worker.get(worker, 0.0)
            mentor_worker_pairs.append(
                {
                    "mentor_model": mentor,
                    "worker_model": worker,
                    "baseline_pass_rate": round(baseline_rate, 4),
                    "mentored_pass_rate": round(pass_rate, 4),
                    "control_pass_rate": round(control_rate, 4),
                    "mentorship_lift": round(pass_rate - baseline_rate, 4),
                    "mentor_violation_rate": round(violation_rate, 4),
                }
            )

    mentor_rankings: list[dict[str, Any]] = []
    for mentor in mentor_models:
        mentor_pairs = [row for row in mentor_worker_pairs if row["mentor_model"] == mentor]
        mentor_runs = [row for row in mentor_worker_runs if row["mentor_model"] == mentor]
        avg_lift = mean(row["mentorship_lift"] for row in mentor_pairs) if mentor_pairs else 0.0
        pass_rate = _rate(mentor_runs)

        total_turns = sum(int(run.get("mentor_turn_count", 0)) for run in mentor_runs)
        total_violations = sum(int(run.get("mentor_violation_count", 0)) for run in mentor_runs)
        violation_rate = (total_violations / total_turns) if total_turns else 0.0

        mentor_rankings.append(
            {
                "mentor_model": mentor,
                "avg_lift_across_workers": round(avg_lift, 4),
                "overall_mentored_pass_rate": round(pass_rate, 4),
                "mentor_violation_rate": round(violation_rate, 4),
            }
        )

    mentor_rankings.sort(
        key=lambda row: (
            row["avg_lift_across_workers"],
            row["overall_mentored_pass_rate"],
            -row["mentor_violation_rate"],
        ),
        reverse=True,
    )

    worker_rankings: list[dict[str, Any]] = []
    for worker in worker_models:
        worker_mentored = [run for run in mentor_worker_runs if run["worker_model"] == worker]
        mentored_rate = _rate(worker_mentored)
        baseline = baseline_by_worker.get(worker, 0.0)
        control = control_by_worker.get(worker, 0.0)
        worker_rankings.append(
            {
                "worker_model": worker,
                "baseline_pass_rate": round(baseline, 4),
                "mentored_pass_rate": round(mentored_rate, 4),
                "control_pass_rate": round(control, 4),
                "delta": round(mentored_rate - baseline, 4),
            }
        )

    worker_rankings.sort(key=lambda row: (row["mentored_pass_rate"], row["baseline_pass_rate"]), reverse=True)

    categories = sorted(set(task_categories.values()))
    category_breakdown: list[dict[str, Any]] = []
    for category in categories:
        ids = {task_id for task_id, task_category in task_categories.items() if task_category == category}
        baseline_cat = [run for run in worker_only_runs if run["task_id"] in ids]
        mentored_cat = [run for run in mentor_worker_runs if run["task_id"] in ids]
        control_cat = [run for run in control_runs if run["task_id"] in ids]

        baseline_rate = _rate(baseline_cat)
        mentored_rate = _rate(mentored_cat)
        control_rate = _rate(control_cat)

        category_breakdown.append(
            {
                "category": category,
                "baseline_pass_rate": round(baseline_rate, 4),
                "mentored_pass_rate": round(mentored_rate, 4),
                "control_pass_rate": round(control_rate, 4),
                "mentorship_lift": round(mentored_rate - baseline_rate, 4),
            }
        )

    category_breakdown.sort(key=lambda row: row["mentorship_lift"], reverse=True)

    return {
        "task_count": len(task_categories),
        "tasks": sorted(task_categories),
        "baseline_by_worker": baseline_by_worker,
        "control_by_worker": control_by_worker,
        "mentor_worker_pairs": mentor_worker_pairs,
        "best_mentors": mentor_rankings,
        "best_workers": worker_rankings,
        "category_breakdown": category_breakdown,
    }


def _to_markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    header = "| " + " | ".join(title for _, title in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        lines.append("| " + " | ".join(str(row[key]) for key, _ in columns) + " |")
    return "\n".join(lines)


def _git_commit_hash() -> str | None:
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return process.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_is_dirty() -> bool | None:
    try:
        process = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return bool(process.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _capture_runtime_context(
    *,
    mentor_client: LLMClient,
    worker_client: LLMClient,
    mentor_models: list[str],
    worker_models: list[str],
    mentor_provider: str,
    worker_provider: str,
) -> dict[str, Any]:
    provider_details: dict[str, dict[str, Any]] = {}

    if isinstance(mentor_client, OllamaClient):
        ollama_models = sorted(set(mentor_models + (worker_models if mentor_provider == worker_provider else [])))
        provider_details["ollama"] = mentor_client.runtime_metadata(ollama_models)
    elif isinstance(worker_client, OllamaClient):
        provider_details["ollama"] = worker_client.runtime_metadata(worker_models)
    else:
        provider_details["ollama"] = {}

    if mentor_provider == "openai":
        openai_models = sorted(set(mentor_models + (worker_models if mentor_provider == worker_provider else [])))
        provider_details["openai"] = mentor_client.runtime_metadata(openai_models)
    elif worker_provider == "openai":
        provider_details["openai"] = worker_client.runtime_metadata(worker_models)
    else:
        provider_details["openai"] = {}

    return {
        "benchmark_version": __version__,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "llm": {
            "mentor_provider": mentor_provider,
            "worker_provider": worker_provider,
        },
        "ollama": provider_details["ollama"],
        "openai": provider_details["openai"],
        "git": {
            "commit": _git_commit_hash(),
            "dirty": _git_is_dirty(),
        },
    }


def _format_rate(value: float) -> str:
    return f"{value:.2%}"


def write_leaderboard(results: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    aggregates = results["aggregates"]
    mentors = aggregates["best_mentors"]
    workers = aggregates["best_workers"]
    pairs = aggregates["mentor_worker_pairs"]
    categories = aggregates.get("category_breakdown", [])

    top_line = "No runs completed."
    if mentors:
        top = mentors[0]
        top_line = (
            f"Top mentor: `{top['mentor_model']}` with average lift {_format_rate(top['avg_lift_across_workers'])}, "
            f"mentored pass rate {_format_rate(top['overall_mentored_pass_rate'])}, "
            f"violation rate {_format_rate(top['mentor_violation_rate'])}."
        )

    mentor_rows = [
        {
            "mentor_model": row["mentor_model"],
            "avg_lift_across_workers": _format_rate(row["avg_lift_across_workers"]),
            "overall_mentored_pass_rate": _format_rate(row["overall_mentored_pass_rate"]),
            "mentor_violation_rate": _format_rate(row["mentor_violation_rate"]),
        }
        for row in mentors
    ]

    worker_rows = [
        {
            "worker_model": row["worker_model"],
            "baseline_pass_rate": _format_rate(row["baseline_pass_rate"]),
            "mentored_pass_rate": _format_rate(row["mentored_pass_rate"]),
            "control_pass_rate": _format_rate(row["control_pass_rate"]),
            "delta": _format_rate(row["delta"]),
        }
        for row in workers
    ]

    pair_rows = [
        {
            "mentor_model": row["mentor_model"],
            "worker_model": row["worker_model"],
            "baseline_pass_rate": _format_rate(row["baseline_pass_rate"]),
            "mentored_pass_rate": _format_rate(row["mentored_pass_rate"]),
            "control_pass_rate": _format_rate(row["control_pass_rate"]),
            "mentorship_lift": _format_rate(row["mentorship_lift"]),
            "mentor_violation_rate": _format_rate(row["mentor_violation_rate"]),
        }
        for row in pairs
    ]

    category_rows = [
        {
            "category": row["category"],
            "baseline_pass_rate": _format_rate(row["baseline_pass_rate"]),
            "mentored_pass_rate": _format_rate(row["mentored_pass_rate"]),
            "control_pass_rate": _format_rate(row["control_pass_rate"]),
            "mentorship_lift": _format_rate(row["mentorship_lift"]),
        }
        for row in categories
    ]

    mentor_table = _to_markdown_table(
        mentor_rows,
        [
            ("mentor_model", "Mentor"),
            ("avg_lift_across_workers", "Avg Lift"),
            ("overall_mentored_pass_rate", "Mentored Pass Rate"),
            ("mentor_violation_rate", "Violation Rate"),
        ],
    )
    worker_table = _to_markdown_table(
        worker_rows,
        [
            ("worker_model", "Worker"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("control_pass_rate", "Control"),
            ("delta", "Lift"),
        ],
    )
    pair_table = _to_markdown_table(
        pair_rows,
        [
            ("mentor_model", "Mentor"),
            ("worker_model", "Worker"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("control_pass_rate", "Control"),
            ("mentorship_lift", "Lift"),
            ("mentor_violation_rate", "Violation Rate"),
        ],
    )
    category_table = _to_markdown_table(
        category_rows,
        [
            ("category", "Category"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("control_pass_rate", "Control"),
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

## Per-Category Breakdown
{category_table}

## Mentor + Worker Pairs
{pair_table}
"""
    output_path.write_text(content, encoding="utf-8")


def run_sanity_check(
    *,
    task_pack: str,
    suite: str | None,
    task_selector: str | None,
    seed: int,
) -> dict[str, Any]:
    selection = resolve_tasks(
        task_pack=task_pack,
        suite=suite,
        legacy_selector=task_selector,
        seed=seed,
    )

    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    expected_failures = 0
    unexpected_passes = 0
    broken_tasks = 0

    for task in selection.tasks:
        temp_dir, workdir = materialize_task(task)
        try:
            test_result = run_pytest(workdir)
            status = "expected_failure"
            if test_result.exit_code == 0:
                status = "unexpected_pass"
                unexpected_passes += 1
            elif test_result.exit_code == 1:
                expected_failures += 1
            else:
                status = "broken_harness"
                broken_tasks += 1

            rows.append(
                {
                    "task_id": task.task_id,
                    "category": task.category,
                    "split": task.split,
                    "status": status,
                    "exit_code": test_result.exit_code,
                    "duration_seconds": round(test_result.duration_seconds, 4),
                }
            )
        finally:
            temp_dir.cleanup()

    elapsed = time.perf_counter() - started
    return {
        "task_pack": selection.task_pack,
        "suite": selection.suite,
        "selector_source": selection.selector_source,
        "task_count": len(selection.tasks),
        "expected_failures": expected_failures,
        "unexpected_passes": unexpected_passes,
        "broken_tasks": broken_tasks,
        "wall_time_seconds": round(elapsed, 4),
        "runs": rows,
    }


def _pick_stronger_worker_model(
    *,
    client: LLMClient,
    current_workers: list[str],
    explicit_model: str | None,
) -> tuple[str | None, str | None]:
    if not isinstance(client, OllamaClient):
        return None, "Run mode `stronger_worker` currently requires `--worker-provider ollama`."

    if explicit_model:
        if explicit_model in current_workers:
            return None, f"Explicit stronger worker `{explicit_model}` already present in worker set."
        if explicit_model not in client.list_local_models():
            return None, f"Explicit stronger worker `{explicit_model}` is not available locally."
        return explicit_model, None

    catalog = client.get_model_catalog()
    by_name = {str(item.get("name")): item for item in catalog if isinstance(item.get("name"), str)}

    def _size(model_name: str) -> float:
        item = by_name.get(model_name, {})
        details = item.get("details", {}) if isinstance(item, dict) else {}
        size_text = details.get("parameter_size", "") if isinstance(details, dict) else ""
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)B", str(size_text))
        return float(match.group(1)) if match else 0.0

    current_max = max((_size(model) for model in current_workers), default=0.0)
    candidates = [name for name in by_name if name not in current_workers and _size(name) > current_max]
    if not candidates:
        return None, "No stronger local worker model detected."

    candidates.sort(key=lambda name: (_size(name), name), reverse=True)
    return candidates[0], None


def run_benchmark(
    config: BenchmarkConfig,
    client: LLMClient | None = None,
    *,
    mentor_client: LLMClient | None = None,
    worker_client: LLMClient | None = None,
) -> dict[str, Any]:
    if mentor_client is None and worker_client is None and client is None:
        client = OllamaClient()
    mentor_client = mentor_client or client
    worker_client = worker_client or client
    if mentor_client is None or worker_client is None:
        raise RuntimeError("Benchmark run is missing mentor or worker client initialization.")

    selection = resolve_tasks(
        task_pack=config.task_pack,
        suite=config.suite,
        legacy_selector=config.task_selector,
        seed=config.seed,
    )
    selected_tasks = selection.tasks

    run_modes = _normalize_run_modes(list(config.run_modes))
    run_mentor_matrix = "mentor_worker" in run_modes or "mentor_swap" in run_modes
    run_worker_only = "worker_only" in run_modes
    run_control = "mentor_only_suggestion_noise" in run_modes

    mentor_models = list(config.mentor_models_override or config.models)
    worker_models = list(config.worker_models_override or config.models)
    mentor_provider = (config.mentor_provider or config.provider).strip().lower()
    worker_provider = (config.worker_provider or config.provider).strip().lower()
    stronger_worker_included: str | None = None
    stronger_worker_status: str | None = None
    if "stronger_worker" in run_modes:
        stronger_candidate, stronger_message = _pick_stronger_worker_model(
            client=worker_client,
            current_workers=worker_models,
            explicit_model=config.stronger_worker_model,
        )
        if stronger_candidate:
            worker_models.append(stronger_candidate)
            stronger_worker_included = stronger_candidate
        stronger_worker_status = stronger_message

    generation = GenerationSettings(
        temperature=REPRO_TEMPERATURE if config.repro_mode else REPRO_TEMPERATURE,
        top_p=REPRO_TOP_P if config.repro_mode else REPRO_TOP_P,
        worker_num_predict=config.worker_num_predict_override or REPRO_WORKER_MAX_TOKENS,
        mentor_num_predict=config.mentor_num_predict_override or REPRO_MENTOR_MAX_TOKENS,
        max_turns=REPRO_MAX_TURNS if config.repro_mode else config.max_turns,
        seed=config.seed,
    )

    worker_template = _load_template("worker_prompt.txt")
    mentor_template = _load_template("mentor_prompt.txt")

    runs: list[dict[str, Any]] = []
    baseline_lookup: dict[tuple[str, str], bool] = {}

    benchmark_start = time.perf_counter()

    if run_worker_only:
        for worker_model in worker_models:
            for task in selected_tasks:
                temp_dir, workdir = materialize_task(task)
                try:
                    task_prompt = read_task_prompt(task)
                    baseline = _baseline_run(
                        client=worker_client,
                        worker_model=worker_model,
                        task_prompt=task_prompt,
                        task_id=task.task_id,
                        worker_template=worker_template,
                        workdir=workdir,
                        generation=generation,
                    )
                    runs.append(baseline)
                    baseline_lookup[(worker_model, task.task_id)] = bool(baseline["pass"])
                finally:
                    temp_dir.cleanup()

    if run_mentor_matrix:
        for mentor_model in mentor_models:
            for worker_model in worker_models:
                for task in selected_tasks:
                    temp_dir, workdir = materialize_task(task)
                    try:
                        task_prompt = read_task_prompt(task)
                        mentored = _mentored_run(
                            worker_client=worker_client,
                            mentor_client=mentor_client,
                            mentor_model=mentor_model,
                            worker_model=worker_model,
                            task_prompt=task_prompt,
                            task_id=task.task_id,
                            worker_template=worker_template,
                            mentor_template=mentor_template,
                            workdir=workdir,
                            generation=generation,
                            mentor_strategy="real",
                        )
                        mentored["baseline_pass"] = baseline_lookup.get((worker_model, task.task_id))
                        runs.append(mentored)
                    finally:
                        temp_dir.cleanup()

    if run_control:
        for worker_model in worker_models:
            for task in selected_tasks:
                temp_dir, workdir = materialize_task(task)
                try:
                    task_prompt = read_task_prompt(task)
                    control = _mentored_run(
                        worker_client=worker_client,
                        mentor_client=mentor_client,
                        mentor_model="dummy_control",
                        worker_model=worker_model,
                        task_prompt=task_prompt,
                        task_id=task.task_id,
                        worker_template=worker_template,
                        mentor_template=mentor_template,
                        workdir=workdir,
                        generation=generation,
                        mentor_strategy="dummy_control",
                    )
                    control["baseline_pass"] = baseline_lookup.get((worker_model, task.task_id))
                    runs.append(control)
                finally:
                    temp_dir.cleanup()

    elapsed = time.perf_counter() - benchmark_start

    task_categories = {task.task_id: task.category for task in selected_tasks}
    aggregates = _compute_aggregates(
        runs=runs,
        worker_models=worker_models,
        mentor_models=mentor_models,
        task_categories=task_categories,
    )

    all_violations: list[dict[str, Any]] = []
    for run in runs:
        violations = run.get("log", {}).get("violations", [])
        if not isinstance(violations, list):
            continue
        for violation in violations:
            if not isinstance(violation, dict):
                continue
            enriched = {
                "mode": run.get("mode"),
                "task_id": run.get("task_id"),
                "worker_model": run.get("worker_model"),
                "mentor_model": run.get("mentor_model"),
                **violation,
            }
            all_violations.append(enriched)

    environment = _capture_runtime_context(
        mentor_client=mentor_client,
        worker_client=worker_client,
        mentor_models=mentor_models,
        worker_models=worker_models,
        mentor_provider=mentor_provider,
        worker_provider=worker_provider,
    )

    run_counts_by_mode: dict[str, int] = {}
    for run in runs:
        mode_name = str(run.get("mode"))
        run_counts_by_mode[mode_name] = run_counts_by_mode.get(mode_name, 0) + 1

    results = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "config": {
            "models": sorted(set(mentor_models + worker_models)),
            "mentor_models": mentor_models,
            "worker_models": worker_models,
            "provider": config.provider,
            "mentor_provider": mentor_provider,
            "worker_provider": worker_provider,
            "run_modes": run_modes,
            "repro_mode": config.repro_mode,
            "max_turns": generation.max_turns,
            "generation": {
                "temperature": generation.temperature,
                "top_p": generation.top_p,
                "worker_num_predict": generation.worker_num_predict,
                "mentor_num_predict": generation.mentor_num_predict,
                "seed": generation.seed,
            },
            "task_pack": config.task_pack,
            "suite": selection.suite,
            "selector_source": selection.selector_source,
            "task_selector": config.task_selector,
            "task_count": len(selected_tasks),
            "stronger_worker_included": stronger_worker_included,
            "stronger_worker_status": stronger_worker_status,
        },
        "environment": environment,
        "summary": {
            "total_runs": len(runs),
            "runs_by_mode": run_counts_by_mode,
            "benchmark_wall_time_seconds": round(elapsed, 4),
            "violation_count": len(all_violations),
        },
        "runs": runs,
        "violations": all_violations,
        "aggregates": aggregates,
    }

    config.results_path.parent.mkdir(parents=True, exist_ok=True)
    config.results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_leaderboard(results, config.results_path.parent / "leaderboard.md")
    return results


def _safe_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def compare_results(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_workers = {
        row["worker_model"]: row
        for row in before.get("aggregates", {}).get("best_workers", [])
        if isinstance(row, dict) and isinstance(row.get("worker_model"), str)
    }
    after_workers = {
        row["worker_model"]: row
        for row in after.get("aggregates", {}).get("best_workers", [])
        if isinstance(row, dict) and isinstance(row.get("worker_model"), str)
    }

    before_mentors = {
        row["mentor_model"]: row
        for row in before.get("aggregates", {}).get("best_mentors", [])
        if isinstance(row, dict) and isinstance(row.get("mentor_model"), str)
    }
    after_mentors = {
        row["mentor_model"]: row
        for row in after.get("aggregates", {}).get("best_mentors", [])
        if isinstance(row, dict) and isinstance(row.get("mentor_model"), str)
    }

    worker_deltas: list[dict[str, Any]] = []
    for worker in sorted(set(before_workers) | set(after_workers)):
        left = before_workers.get(worker, {})
        right = after_workers.get(worker, {})
        worker_deltas.append(
            {
                "worker_model": worker,
                "baseline_delta": round(
                    _safe_float(right.get("baseline_pass_rate"))
                    - _safe_float(left.get("baseline_pass_rate")),
                    4,
                ),
                "mentored_delta": round(
                    _safe_float(right.get("mentored_pass_rate"))
                    - _safe_float(left.get("mentored_pass_rate")),
                    4,
                ),
                "control_delta": round(
                    _safe_float(right.get("control_pass_rate"))
                    - _safe_float(left.get("control_pass_rate")),
                    4,
                ),
                "lift_delta": round(
                    _safe_float(right.get("delta")) - _safe_float(left.get("delta")),
                    4,
                ),
            }
        )

    mentor_deltas: list[dict[str, Any]] = []
    for mentor in sorted(set(before_mentors) | set(after_mentors)):
        left = before_mentors.get(mentor, {})
        right = after_mentors.get(mentor, {})
        mentor_deltas.append(
            {
                "mentor_model": mentor,
                "avg_lift_delta": round(
                    _safe_float(right.get("avg_lift_across_workers"))
                    - _safe_float(left.get("avg_lift_across_workers")),
                    4,
                ),
                "pass_rate_delta": round(
                    _safe_float(right.get("overall_mentored_pass_rate"))
                    - _safe_float(left.get("overall_mentored_pass_rate")),
                    4,
                ),
                "violation_rate_delta": round(
                    _safe_float(right.get("mentor_violation_rate"))
                    - _safe_float(left.get("mentor_violation_rate")),
                    4,
                ),
            }
        )

    return {
        "before": {
            "generated_at": before.get("generated_at"),
            "total_runs": before.get("summary", {}).get("total_runs", 0),
            "wall_time_seconds": before.get("summary", {}).get("benchmark_wall_time_seconds", 0),
        },
        "after": {
            "generated_at": after.get("generated_at"),
            "total_runs": after.get("summary", {}).get("total_runs", 0),
            "wall_time_seconds": after.get("summary", {}).get("benchmark_wall_time_seconds", 0),
        },
        "delta": {
            "total_runs": int(after.get("summary", {}).get("total_runs", 0))
            - int(before.get("summary", {}).get("total_runs", 0)),
            "wall_time_seconds": round(
                _safe_float(after.get("summary", {}).get("benchmark_wall_time_seconds", 0))
                - _safe_float(before.get("summary", {}).get("benchmark_wall_time_seconds", 0)),
                4,
            ),
        },
        "worker_deltas": worker_deltas,
        "mentor_deltas": mentor_deltas,
    }


def render_compare_report(comparison: dict[str, Any]) -> str:
    lines = [
        "Benchmark Comparison (after - before)",
        f"Before: {comparison['before']['generated_at']} ({comparison['before']['total_runs']} runs)",
        f"After:  {comparison['after']['generated_at']} ({comparison['after']['total_runs']} runs)",
        f"Delta total runs: {comparison['delta']['total_runs']}",
        f"Delta wall time (s): {comparison['delta']['wall_time_seconds']}",
        "",
        "Worker deltas:",
    ]

    for row in comparison.get("worker_deltas", []):
        lines.append(
            "- "
            f"{row['worker_model']}: baseline {row['baseline_delta']:+.4f}, "
            f"mentored {row['mentored_delta']:+.4f}, control {row['control_delta']:+.4f}, "
            f"lift {row['lift_delta']:+.4f}"
        )

    lines.append("")
    lines.append("Mentor deltas:")
    for row in comparison.get("mentor_deltas", []):
        lines.append(
            "- "
            f"{row['mentor_model']}: avg lift {row['avg_lift_delta']:+.4f}, "
            f"pass rate {row['pass_rate_delta']:+.4f}, "
            f"violation rate {row['violation_rate_delta']:+.4f}"
        )

    return "\n".join(lines)
