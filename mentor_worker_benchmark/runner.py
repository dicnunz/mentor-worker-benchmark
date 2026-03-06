from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from mentor_worker_benchmark import __version__
from mentor_worker_benchmark.checkpointing import BenchmarkCheckpointStore, RunUnitKey
from mentor_worker_benchmark.llm_client import LLMClient
from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.protocol import deterministic_run_group_id
from mentor_worker_benchmark.tasks.task_codegen_py.harness import (
    materialize_task,
    normalize_pytest_output,
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

REPRO_WORKER_MAX_TOKENS = 640
REPRO_MENTOR_MAX_TOKENS = 220
REPRO_TEMPERATURE = 0.0
REPRO_TOP_P = 1.0

WORKER_SYSTEM_PROMPT = (
    "You are a precise coding agent. Return only a valid unified diff patch and nothing else. "
    "Patch against the current file state shown in the prompt and remove obsolete buggy lines instead of leaving duplicate logic."
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
MALFORMED_HUNK_RE = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+\+\+\s+.*$")
HUNK_HEADER_RE = re.compile(r"^@@\s*-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@")
HUNK_START_RE = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")
MENTOR_CODE_BLOCK_MAX_LINES = 8
TIMEOUT_TOKEN_RE = re.compile(r"(timed out|\btimeout\b)", re.IGNORECASE)


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
    task_pack_path: Path | None = None
    suite: str | None = None
    task_selector: str | None = None
    seed: int = 1337
    results_path: Path = Path("results/results.json")
    run_modes: tuple[str, ...] = DEFAULT_RUN_MODES
    repro_mode: bool = False
    stronger_worker_model: str | None = None
    worker_num_predict_override: int | None = None
    mentor_num_predict_override: int | None = None
    timeout_seconds: int = 180
    test_timeout_seconds: int = 8
    model_retry_attempts: int = 1
    model_retry_backoff_seconds: float = 1.0


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


@dataclass(slots=True)
class ParsedHunk:
    old_start: int
    body_lines: list[str]


@dataclass(slots=True)
class ParsedFilePatch:
    path: str
    hunks: list[ParsedHunk]


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


def _checkpoint_path_for_results(results_path: Path) -> Path:
    return results_path.with_name(f"{results_path.stem}.checkpoint.jsonl")


def _seed_results_path(results_path: Path, seed: int) -> Path:
    return results_path.with_name(f"{results_path.stem}.seed-{int(seed)}{results_path.suffix}")


def _run_unit_key(
    *,
    seed: int,
    mode: str,
    task_id: str,
    worker_model: str,
    mentor_model: str | None,
) -> RunUnitKey:
    return RunUnitKey(
        seed=int(seed),
        mode=mode,
        task_id=task_id,
        worker_model=worker_model,
        mentor_model=mentor_model,
    )


def _run_pytest_deterministic(
    workdir: Path,
    *,
    evaluation_seed: int,
    timeout_seconds: int,
) -> Any:
    result = run_pytest(
        workdir,
        timeout_seconds=timeout_seconds,
        pythonhashseed=evaluation_seed,
    )
    normalized_output = normalize_pytest_output(result.output)
    if normalized_output == result.output:
        return result
    return replace(result, output=normalized_output)


def _is_transient_model_error(message: str) -> bool:
    lowered = message.lower()
    transient_markers = (
        "timed out",
        "timeout",
        "connection refused",
        "connection reset",
        "temporarily unavailable",
        "http 502",
        "http 503",
        "http 504",
        "unexpected ollama response format",
    )
    return any(marker in lowered for marker in transient_markers)


def _call_model_with_retries(
    *,
    client: LLMClient,
    retry_attempts: int,
    retry_backoff_seconds: float,
    **chat_kwargs: Any,
) -> tuple[str, str | None, int]:
    attempts = 0
    max_attempts = max(1, 1 + int(retry_attempts))
    last_error: str | None = None

    while attempts < max_attempts:
        attempts += 1
        try:
            return client.chat(**chat_kwargs), None, attempts - 1
        except RuntimeError as exc:
            last_error = str(exc)
            if attempts >= max_attempts or not _is_transient_model_error(last_error):
                break
            backoff = max(0.0, float(retry_backoff_seconds)) * attempts
            if backoff > 0:
                time.sleep(backoff)

    assert last_error is not None  # pragma: no cover - guarded by RuntimeError branch above
    return "", last_error, attempts - 1


def _hash_patch_text(patch_text: str | None) -> str | None:
    if patch_text is None:
        return None
    return hashlib.sha256(patch_text.encode("utf-8")).hexdigest()


def _is_patch_text_valid_length(patch_text: str | None) -> bool:
    if patch_text is None:
        return False
    return len(patch_text.strip()) >= 5


def _assert_tests_executed(test_result: Any, *, task_id: str, mode: str, phase: str) -> None:
    tests_executed = int(getattr(test_result, "tests_executed", 0) or 0)
    if tests_executed <= 0:
        raise RuntimeError(
            "No tests executed for "
            f"task `{task_id}` (mode={mode}, phase={phase}). "
            "Aborting benchmark run."
        )


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

    in_hunk = False
    expected_old = 0
    expected_new = 0
    seen_old = 0
    seen_new = 0
    checked_paths = 0
    def _finalize_hunk() -> tuple[bool, str]:
        if not in_hunk:
            return True, "ok"
        if seen_old != expected_old or seen_new != expected_new:
            return (
                False,
                (
                    "Hunk line counts do not match header "
                    f"(expected -{expected_old}/+{expected_new}, observed -{seen_old}/+{seen_new})."
                ),
            )
        return True, "ok"

    for line in diff_text.splitlines():
        if line.startswith("@@") and not HUNK_HEADER_RE.match(line):
            return False, f"Malformed hunk header `{line}`."
        if line.startswith("@@"):
            ok, message = _finalize_hunk()
            if not ok:
                return False, message
            header = HUNK_START_RE.match(line)
            if not header:
                return False, f"Malformed hunk header `{line}`."
            expected_old = int(header.group(2) or "1")
            expected_new = int(header.group(4) or "1")
            seen_old = 0
            seen_new = 0
            in_hunk = True
            continue

        if line.startswith(("diff --git", "--- ", "+++ ")):
            ok, message = _finalize_hunk()
            if not ok:
                return False, message
            in_hunk = False

        if in_hunk and not line:
            return False, "Malformed hunk body line `empty`."
        if in_hunk and line and not line.startswith((" ", "+", "-", "\\ No newline")):
            return False, f"Malformed hunk body line `{line}`."
        if in_hunk and line.startswith("\\ No newline"):
            continue
        if in_hunk:
            marker = line[0] if line else ""
            if marker in {" ", "-"}:
                seen_old += 1
            if marker in {" ", "+"}:
                seen_new += 1

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

    ok, message = _finalize_hunk()
    if not ok:
        return False, message

    return True, "ok"


def _sanitize_diff_candidate(diff_text: str) -> str:
    normalized = diff_text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = normalized.splitlines()
    stripped_lines: list[str] = []
    for raw_line in raw_lines:
        line = raw_line
        # Some models escape leading diff syntax with a backslash; strip one layer.
        if line.startswith("\\"):
            candidate = line[1:]
            if not candidate or candidate[0] in {" ", "+", "-", "@", "#", "\t"}:
                line = candidate
        stripped_lines.append(line.rstrip())

    sanitized_lines: list[str] = []
    i = 0
    while i < len(stripped_lines):
        line = stripped_lines[i]
        malformed_hunk = MALFORMED_HUNK_RE.match(line)
        if malformed_hunk:
            start = malformed_hunk.group(1)
            count = malformed_hunk.group(2) or "1"
            line = f"@@ -{start},{count} +{start},{count} @@"

        if line.startswith("@@"):
            start_match = HUNK_START_RE.match(line)
            old_start = int(start_match.group(1)) if start_match else 1
            new_start = int(start_match.group(3)) if start_match else old_start

            body: list[str] = []
            i += 1
            while i < len(stripped_lines):
                next_line = stripped_lines[i]
                if next_line.startswith(("@@", "--- ")):
                    break
                if next_line.startswith("+++ ") and body:
                    break
                if next_line.startswith("\\ No newline at end of file"):
                    body.append(next_line)
                else:
                    if next_line == "":
                        # Unified diffs represent empty context/add/remove lines with a leading marker.
                        next_line = " "
                    elif len(next_line) >= 3 and next_line[0] in {" ", "+", "-"} and next_line[1:3] == "\\n":
                        # Some model outputs embed a literal "\n" token after the diff marker.
                        next_line = next_line[0] + next_line[3:]
                    if next_line and next_line[0] not in {" ", "+", "-"}:
                        next_line = f" {next_line}"
                    body.append(next_line)
                i += 1

            old_count = sum(
                1
                for item in body
                if item and item[0] in {" ", "-"}
            )
            new_count = sum(
                1
                for item in body
                if item and item[0] in {" ", "+"}
            )
            old_count = max(1, old_count)
            new_count = max(1, new_count)
            sanitized_lines.append(f"@@ -{old_start},{old_count} +{new_start},{new_count} @@")
            sanitized_lines.extend(body)
            continue

        sanitized_lines.append(line)
        i += 1

    return "\n".join(sanitized_lines).strip() + "\n"


def _extract_diff(text: str) -> str | None:
    text = text.strip()
    blocks = [block.strip() for block in DIFF_BLOCK_RE.findall(text)]
    candidates = blocks + [text]

    for candidate in candidates:
        repaired = _sanitize_diff_candidate(candidate)
        valid_repaired, _ = _validate_patch_format(repaired)
        if valid_repaired:
            return repaired
        valid, _ = _validate_patch_format(candidate)
        if valid:
            return f"{candidate}\n"
    return None


def _parse_unified_diff(diff_text: str) -> tuple[list[ParsedFilePatch], str | None]:
    lines = diff_text.splitlines()
    parsed: list[ParsedFilePatch] = []
    current: ParsedFilePatch | None = None
    index = 0

    while index < len(lines):
        line = lines[index]
        if line.startswith("--- "):
            if index + 1 >= len(lines) or not lines[index + 1].startswith("+++ "):
                return [], "Heuristic apply parse error: missing `+++` file header."
            normalized = _normalize_patch_path(lines[index + 1][4:])
            if not normalized:
                return [], "Heuristic apply parse error: patch references /dev/null file."
            current = ParsedFilePatch(path=normalized, hunks=[])
            parsed.append(current)
            index += 2
            continue

        if line.startswith("@@"):
            if current is None:
                return [], "Heuristic apply parse error: hunk appeared before file header."
            match = HUNK_START_RE.match(line)
            if not match:
                return [], f"Heuristic apply parse error: malformed hunk header `{line}`."
            old_start = int(match.group(1))
            body_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@", "--- ")):
                body_lines.append(lines[index])
                index += 1
            current.hunks.append(ParsedHunk(old_start=old_start, body_lines=body_lines))
            continue

        index += 1

    if not parsed:
        return [], "Heuristic apply parse error: no file patches found."
    return parsed, None


def _find_subsequence_window(
    file_lines: list[str],
    old_lines: list[str],
    *,
    start_at: int,
) -> tuple[int, int] | None:
    if not old_lines:
        return (max(0, min(start_at, len(file_lines))), max(0, min(start_at, len(file_lines))))

    anchors = [line for line in old_lines if line.strip()]
    if len(anchors) < 2:
        return None

    matched: list[int] = []
    cursor = max(0, start_at)
    for needle in old_lines:
        found_at: int | None = None
        for idx in range(cursor, len(file_lines)):
            if file_lines[idx] == needle:
                found_at = idx
                break
        if found_at is None:
            return None
        matched.append(found_at)
        cursor = found_at + 1

    start = matched[0]
    end_exclusive = matched[-1] + 1
    max_window = len(old_lines) + 120
    if end_exclusive - start > max_window:
        return None

    return (start, end_exclusive)


def _apply_patch_heuristic(workdir: Path, diff_text: str) -> tuple[bool, str]:
    parsed, parse_error = _parse_unified_diff(diff_text)
    if parse_error:
        return False, parse_error

    logs: list[str] = []
    for file_patch in parsed:
        target_path = workdir / file_patch.path
        if not target_path.exists():
            return False, f"Heuristic apply failed: target file `{file_patch.path}` does not exist."

        original_text = target_path.read_text(encoding="utf-8")
        had_trailing_newline = original_text.endswith("\n")
        file_lines = original_text.splitlines()
        cursor = 0

        for hunk_index, hunk in enumerate(file_patch.hunks, start=1):
            old_lines: list[str] = []
            new_lines: list[str] = []
            for line in hunk.body_lines:
                if line.startswith("\\ No newline"):
                    continue
                if not line:
                    marker = " "
                    payload = ""
                else:
                    marker = line[0]
                    payload = line[1:]
                if marker in {" ", "-"}:
                    old_lines.append(payload)
                if marker in {" ", "+"}:
                    new_lines.append(payload)

            hint_index = max(0, hunk.old_start - 1)
            replace_start: int | None = None
            replace_end_exclusive: int | None = None

            if old_lines:
                if hint_index + len(old_lines) <= len(file_lines):
                    if file_lines[hint_index : hint_index + len(old_lines)] == old_lines:
                        replace_start = hint_index
                        replace_end_exclusive = hint_index + len(old_lines)

                if replace_start is None:
                    for idx in range(0, len(file_lines) - len(old_lines) + 1):
                        if file_lines[idx : idx + len(old_lines)] == old_lines:
                            replace_start = idx
                            replace_end_exclusive = idx + len(old_lines)
                            break
            else:
                bounded = max(0, min(hint_index, len(file_lines)))
                replace_start = bounded
                replace_end_exclusive = bounded

            if replace_start is None or replace_end_exclusive is None:
                subsequence = _find_subsequence_window(
                    file_lines,
                    old_lines,
                    start_at=cursor,
                )
                if subsequence is None:
                    return (
                        False,
                        (
                            "Heuristic apply failed: unable to match hunk "
                            f"{hunk_index} in `{file_patch.path}`."
                        ),
                    )
                replace_start, replace_end_exclusive = subsequence
                logs.append(
                    f"Heuristic hunk {hunk_index} for `{file_patch.path}` applied via ordered-subsequence match."
                )
            else:
                logs.append(
                    f"Heuristic hunk {hunk_index} for `{file_patch.path}` applied via exact match."
                )

            file_lines[replace_start:replace_end_exclusive] = new_lines
            cursor = replace_start + len(new_lines)

        updated_text = "\n".join(file_lines)
        if had_trailing_newline or updated_text:
            updated_text += "\n"
        target_path.write_text(updated_text, encoding="utf-8")

    return True, "\n".join(logs)


def _apply_patch(workdir: Path, diff_text: str) -> tuple[bool, str]:
    valid, reason = _validate_patch_format(diff_text)
    if not valid:
        return False, reason

    sanitized = _sanitize_diff_candidate(diff_text)
    patch_variants: list[tuple[str, str]] = [("input", diff_text)]
    if sanitized != diff_text:
        repaired_valid, _ = _validate_patch_format(sanitized)
        if repaired_valid:
            patch_variants.append(("sanitized", sanitized))

    attempts = [
        ["patch", "-p0", "--batch", "--forward", "--reject-file=-"],
        ["patch", "-p1", "--batch", "--forward", "--reject-file=-"],
    ]

    logs: list[str] = []
    for variant_name, patch_text in patch_variants:
        for command in attempts:
            try:
                process = subprocess.run(
                    command,
                    cwd=workdir,
                    input=patch_text,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=12,
                )
                logs.append(f"[{variant_name}] $ {' '.join(command)}\n{process.stdout}")
                if process.returncode == 0:
                    return True, "\n".join(logs)
            except subprocess.TimeoutExpired:
                logs.append(f"[{variant_name}] $ {' '.join(command)}\n[timeout] patch command timed out")

    heuristic_ok, heuristic_log = _apply_patch_heuristic(workdir, diff_text)
    logs.append(f"[heuristic]\n{heuristic_log}")
    if heuristic_ok:
        return True, "\n".join(logs)

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
    task_family_id: str | None,
    worker_template: str,
    workdir: Path,
    generation: GenerationSettings,
    test_timeout_seconds: int,
    model_retry_attempts: int,
    model_retry_backoff_seconds: float,
) -> dict[str, Any]:
    start = time.perf_counter()
    evaluation_seed = _seed_for_call(generation.seed, "evaluation", "worker_only", worker_model, task_id)
    initial_tests = _run_pytest_deterministic(
        workdir,
        evaluation_seed=evaluation_seed,
        timeout_seconds=test_timeout_seconds,
    )
    _assert_tests_executed(initial_tests, task_id=task_id, mode="worker_only", phase="initial")
    snapshot = project_snapshot(workdir)
    worker_prompt = _render_worker_prompt(
        template=worker_template,
        task_prompt=task_prompt,
        snapshot=snapshot,
        failure_output=initial_tests.output,
        mentor_guidance="(none)",
    )

    worker_seed = _seed_for_call(generation.seed, "worker_only", worker_model, task_id)
    worker_response, worker_error, worker_retry_count = _call_model_with_retries(
        client=client,
        retry_attempts=model_retry_attempts,
        retry_backoff_seconds=model_retry_backoff_seconds,
        model=worker_model,
        messages=[{"role": "user", "content": worker_prompt}],
        system=WORKER_SYSTEM_PROMPT,
        temperature=generation.temperature,
        top_p=generation.top_p,
        num_predict=generation.worker_num_predict,
        seed=worker_seed,
    )
    if worker_error:
        worker_response = f"[worker_error] {worker_error}"

    extracted = _extract_diff(worker_response)
    patch_hash = _hash_patch_text(extracted)
    patch_length = len(extracted.strip()) if extracted else 0
    patch_valid_length = _is_patch_text_valid_length(extracted)
    patch_applied = False
    patch_log = "No valid unified diff found in worker response."
    if extracted and not patch_valid_length:
        patch_log = "Patch too short (<5 chars); marked invalid."
    elif extracted:
        patch_applied, patch_log = _apply_patch(workdir, extracted)
    elif worker_error:
        patch_log = worker_error

    final_tests = (
        initial_tests
        if not patch_applied
        else _run_pytest_deterministic(
            workdir,
            evaluation_seed=evaluation_seed,
            timeout_seconds=test_timeout_seconds,
        )
    )
    _assert_tests_executed(final_tests, task_id=task_id, mode="worker_only", phase="final")
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
        "task_family_id": task_family_id,
        "seed": generation.seed,
        "evaluation_seed": evaluation_seed,
        "worker_model": worker_model,
        "mentor_model": None,
        "pass": final_tests.passed,
        "turns_used": 1,
        "wall_time_seconds": round(elapsed, 4),
        "total_tokens_estimate": total_tokens,
        "patch_hash": patch_hash,
        "test_runtime_seconds": round(final_tests.duration_seconds, 4),
        "tests_executed": int(final_tests.tests_executed),
        "tests_passed": int(final_tests.tests_passed),
        "tests_failed": int(final_tests.tests_failed),
        "mentor_turn_count": 0,
        "mentor_violation_count": 0,
        "execution_evidence": {
            "initial_test_runtime_seconds": round(initial_tests.duration_seconds, 4),
            "initial_tests_executed": int(initial_tests.tests_executed),
            "initial_tests_passed": int(initial_tests.tests_passed),
            "initial_tests_failed": int(initial_tests.tests_failed),
            "final_test_runtime_seconds": round(final_tests.duration_seconds, 4),
            "final_tests_executed": int(final_tests.tests_executed),
            "final_tests_passed": int(final_tests.tests_passed),
            "final_tests_failed": int(final_tests.tests_failed),
            "patch_hash": patch_hash,
            "patch_length": patch_length,
            "patch_length_valid": patch_valid_length,
            "evaluation_seed": evaluation_seed,
            "worker_retry_count": worker_retry_count,
        },
        "log": {
            "initial_test_output": initial_tests.output,
            "worker_prompt": worker_prompt,
            "worker_response": worker_response,
            "worker_error": worker_error,
            "worker_retry_count": worker_retry_count,
            "extracted_patch": extracted,
            "patch_hash": patch_hash,
            "patch_length": patch_length,
            "patch_length_valid": patch_valid_length,
            "evaluation_seed": evaluation_seed,
            "patch_applied": patch_applied,
            "patch_log": patch_log,
            "final_test_output": final_tests.output,
            "initial_test_stats": {
                "tests_executed": int(initial_tests.tests_executed),
                "tests_passed": int(initial_tests.tests_passed),
                "tests_failed": int(initial_tests.tests_failed),
                "duration_seconds": round(initial_tests.duration_seconds, 4),
            },
            "final_test_stats": {
                "tests_executed": int(final_tests.tests_executed),
                "tests_passed": int(final_tests.tests_passed),
                "tests_failed": int(final_tests.tests_failed),
                "duration_seconds": round(final_tests.duration_seconds, 4),
            },
        },
    }


def _mentored_run(
    worker_client: LLMClient,
    mentor_client: LLMClient,
    mentor_model: str,
    worker_model: str,
    task_prompt: str,
    task_id: str,
    task_family_id: str | None,
    worker_template: str,
    mentor_template: str,
    workdir: Path,
    generation: GenerationSettings,
    mentor_strategy: Literal["real", "dummy_control"] = "real",
    test_timeout_seconds: int = 8,
    model_retry_attempts: int = 1,
    model_retry_backoff_seconds: float = 1.0,
) -> dict[str, Any]:
    effective_mode = "mentor_worker" if mentor_strategy == "real" else "mentor_only_suggestion_noise"
    start = time.perf_counter()
    guidance_history: list[str] = []
    turns: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    patch_hashes: list[str] = []
    evaluation_seed = _seed_for_call(
        generation.seed,
        "evaluation",
        mentor_strategy,
        mentor_model,
        worker_model,
        task_id,
    )

    current_tests = _run_pytest_deterministic(
        workdir,
        evaluation_seed=evaluation_seed,
        timeout_seconds=test_timeout_seconds,
    )
    _assert_tests_executed(current_tests, task_id=task_id, mode=effective_mode, phase="initial")
    token_accumulator = _estimate_tokens(current_tests.output)
    passed = current_tests.passed
    initial_test_result = current_tests
    final_patch_hash: str | None = None
    cached_snapshot: str | None = None

    for turn_index in range(1, generation.max_turns + 1):
        if cached_snapshot is None:
            cached_snapshot = project_snapshot(workdir)
        snapshot = cached_snapshot
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
        worker_response, worker_error, worker_retry_count = _call_model_with_retries(
            client=worker_client,
            retry_attempts=model_retry_attempts,
            retry_backoff_seconds=model_retry_backoff_seconds,
            model=worker_model,
            messages=[{"role": "user", "content": worker_prompt}],
            system=WORKER_SYSTEM_PROMPT,
            temperature=generation.temperature,
            top_p=generation.top_p,
            num_predict=generation.worker_num_predict,
            seed=worker_seed,
        )
        if worker_error:
            worker_response = f"[worker_error] {worker_error}"

        token_accumulator += _estimate_tokens(worker_prompt) + _estimate_tokens(worker_response)
        extracted = _extract_diff(worker_response)
        patch_hash = _hash_patch_text(extracted)
        patch_length = len(extracted.strip()) if extracted else 0
        patch_valid_length = _is_patch_text_valid_length(extracted)
        if patch_hash:
            patch_hashes.append(patch_hash)
            final_patch_hash = patch_hash
        patch_applied = False
        patch_log = "No valid unified diff found in worker response."
        if extracted and not patch_valid_length:
            patch_log = "Patch too short (<5 chars); marked invalid."
        elif extracted:
            patch_applied, patch_log = _apply_patch(workdir, extracted)
        elif worker_error:
            patch_log = worker_error

        if patch_applied:
            current_tests = _run_pytest_deterministic(
                workdir,
                evaluation_seed=evaluation_seed,
                timeout_seconds=test_timeout_seconds,
            )
            cached_snapshot = None
        _assert_tests_executed(
            current_tests,
            task_id=task_id,
            mode=effective_mode,
            phase=f"turn_{turn_index}",
        )
        token_accumulator += _estimate_tokens(current_tests.output)
        passed = current_tests.passed

        turn_log: dict[str, Any] = {
            "turn": turn_index,
            "worker_prompt": worker_prompt,
            "worker_response": worker_response,
            "worker_error": worker_error,
            "worker_retry_count": worker_retry_count,
            "extracted_patch": extracted,
            "patch_hash": patch_hash,
            "patch_length": patch_length,
            "patch_length_valid": patch_valid_length,
            "patch_applied": patch_applied,
            "patch_log": patch_log,
            "test_output": current_tests.output,
            "pass_after_turn": passed,
            "test_runtime_seconds": round(current_tests.duration_seconds, 4),
            "tests_executed": int(current_tests.tests_executed),
            "tests_passed": int(current_tests.tests_passed),
            "tests_failed": int(current_tests.tests_failed),
            "evaluation_seed": evaluation_seed,
        }

        if worker_error:
            turn_log["early_stop_reason"] = "worker_request_error"
            turns.append(turn_log)
            break

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
            mentor_retry_count = 0
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
                mentor_response, mentor_error, mentor_retry_count = _call_model_with_retries(
                    client=mentor_client,
                    retry_attempts=model_retry_attempts,
                    retry_backoff_seconds=model_retry_backoff_seconds,
                    model=mentor_model,
                    messages=[{"role": "user", "content": mentor_prompt}],
                    system=MENTOR_SYSTEM_PROMPT,
                    temperature=generation.temperature,
                    top_p=generation.top_p,
                    num_predict=generation.mentor_num_predict,
                    seed=mentor_seed,
                )
                if mentor_error:
                    mentor_response = f"[mentor_error] {mentor_error}"

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
            turn_log["mentor_retry_count"] = mentor_retry_count
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
    mode_name = effective_mode
    mentor_turn_count = sum(1 for turn in turns if "mentor_prompt" in turn)

    return {
        "mode": mode_name,
        "task_id": task_id,
        "task_family_id": task_family_id,
        "seed": generation.seed,
        "evaluation_seed": evaluation_seed,
        "worker_model": worker_model,
        "mentor_model": mentor_model,
        "pass": passed,
        "turns_used": len(turns),
        "wall_time_seconds": round(elapsed, 4),
        "total_tokens_estimate": token_accumulator,
        "patch_hash": final_patch_hash,
        "patch_hashes": patch_hashes,
        "test_runtime_seconds": round(current_tests.duration_seconds, 4),
        "tests_executed": int(current_tests.tests_executed),
        "tests_passed": int(current_tests.tests_passed),
        "tests_failed": int(current_tests.tests_failed),
        "mentor_turn_count": mentor_turn_count,
        "mentor_violation_count": len(violations),
        "execution_evidence": {
            "initial_test_runtime_seconds": round(initial_test_result.duration_seconds, 4),
            "initial_tests_executed": int(initial_test_result.tests_executed),
            "initial_tests_passed": int(initial_test_result.tests_passed),
            "initial_tests_failed": int(initial_test_result.tests_failed),
            "final_test_runtime_seconds": round(current_tests.duration_seconds, 4),
            "final_tests_executed": int(current_tests.tests_executed),
            "final_tests_passed": int(current_tests.tests_passed),
            "final_tests_failed": int(current_tests.tests_failed),
            "patch_hashes": patch_hashes,
            "final_patch_hash": final_patch_hash,
            "evaluation_seed": evaluation_seed,
        },
        "log": {
            "task_prompt": task_prompt,
            "turns": turns,
            "violations": violations,
            "initial_test_stats": {
                "tests_executed": int(initial_test_result.tests_executed),
                "tests_passed": int(initial_test_result.tests_passed),
                "tests_failed": int(initial_test_result.tests_failed),
                "duration_seconds": round(initial_test_result.duration_seconds, 4),
            },
            "final_test_stats": {
                "tests_executed": int(current_tests.tests_executed),
                "tests_passed": int(current_tests.tests_passed),
                "tests_failed": int(current_tests.tests_failed),
                "duration_seconds": round(current_tests.duration_seconds, 4),
            },
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


def _capture_pip_freeze_hash() -> tuple[str, int]:
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pip", "freeze", "--all"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unavailable", 0

    lines = sorted(line.strip() for line in process.stdout.splitlines() if line.strip())
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return digest, len(lines)


def _model_version_rows(
    *,
    provider: str,
    models: list[str],
    provider_metadata: dict[str, Any],
) -> list[dict[str, str]]:
    model_tags = provider_metadata.get("model_tags", [])
    tags_by_name: dict[str, dict[str, Any]] = {}
    if isinstance(model_tags, list):
        for item in model_tags:
            if not isinstance(item, dict):
                continue
            candidates = (
                item.get("name"),
                item.get("model"),
                item.get("id"),
            )
            for candidate in candidates:
                if isinstance(candidate, str) and candidate:
                    tags_by_name.setdefault(candidate, item)

    rows: list[dict[str, str]] = []
    for model in sorted(set(models)):
        metadata = tags_by_name.get(model, {})
        version = ""
        if isinstance(metadata, dict):
            for key in ("digest", "id", "model", "name", "modified_at"):
                value = metadata.get(key)
                if isinstance(value, str) and value.strip():
                    version = value.strip()
                    break
        if not version:
            version = model
        rows.append(
            {
                "provider": provider,
                "model": model,
                "version": version,
            }
        )
    return rows


def _capture_runtime_context(
    *,
    mentor_client: LLMClient,
    worker_client: LLMClient,
    mentor_models: list[str],
    worker_models: list[str],
    mentor_provider: str,
    worker_provider: str,
    task_pack_id: str,
    task_pack_version: str | None,
    task_pack_source: str,
    task_pack_hash: str | None,
    task_pack_manifest_path: str | None,
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

    pip_freeze_sha256, pip_freeze_line_count = _capture_pip_freeze_hash()
    git_commit = _git_commit_hash()
    git_dirty = _git_is_dirty()

    model_versions = sorted(
        _model_version_rows(
            provider=mentor_provider,
            models=mentor_models,
            provider_metadata=provider_details.get(mentor_provider, {}),
        )
        + _model_version_rows(
            provider=worker_provider,
            models=worker_models,
            provider_metadata=provider_details.get(worker_provider, {}),
        ),
        key=lambda row: (row["provider"], row["model"], row["version"]),
    )
    os_label = f"{platform.system()} {platform.release()}".strip()
    python_version = platform.python_version()
    architecture = platform.machine()

    return {
        "benchmark_version": __version__,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "pip_freeze_sha256": pip_freeze_sha256,
            "pip_freeze_line_count": pip_freeze_line_count,
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
            "commit": git_commit,
            "dirty": git_dirty,
        },
        "reproducibility": {
            "python_version": python_version,
            "os": os_label,
            "cpu_architecture": architecture,
            "model_versions": model_versions,
            "commit_hash": git_commit,
        },
        "task_pack": {
            "id": task_pack_id,
            "version": task_pack_version,
            "source": task_pack_source,
            "hash": task_pack_hash,
            "manifest_path": task_pack_manifest_path,
        },
    }


def _build_checkpoint_metadata(
    *,
    config: BenchmarkConfig,
    selection: Any,
    run_modes: list[str],
    mentor_models: list[str],
    worker_models: list[str],
    generation: GenerationSettings,
    mentor_provider: str,
    worker_provider: str,
) -> dict[str, Any]:
    return {
        "benchmark_version": __version__,
        "git_commit": _git_commit_hash(),
        "task_pack": selection.task_pack,
        "task_pack_version": selection.pack_version,
        "task_pack_hash": selection.pack_hash,
        "suite": selection.suite,
        "selector_source": selection.selector_source,
        "seed": int(config.seed),
        "task_ids": [task.task_id for task in selection.tasks],
        "run_modes": list(run_modes),
        "mentor_models": list(mentor_models),
        "worker_models": list(worker_models),
        "provider": config.provider,
        "mentor_provider": mentor_provider,
        "worker_provider": worker_provider,
        "repro_mode": bool(config.repro_mode),
        "max_turns": int(generation.max_turns),
        "worker_num_predict": int(generation.worker_num_predict),
        "mentor_num_predict": int(generation.mentor_num_predict),
        "model_timeout_seconds": int(config.timeout_seconds),
        "test_timeout_seconds": int(config.test_timeout_seconds),
        "model_retry_attempts": int(config.model_retry_attempts),
        "model_retry_backoff_seconds": float(config.model_retry_backoff_seconds),
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
    task_pack_path: Path | None,
    suite: str | None,
    task_selector: str | None,
    seed: int,
) -> dict[str, Any]:
    selection = resolve_tasks(
        task_pack=task_pack,
        task_pack_path=task_pack_path,
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
            evaluation_seed = _seed_for_call(seed, "sanity", task.task_id)
            test_result = _run_pytest_deterministic(
                workdir,
                evaluation_seed=evaluation_seed,
                timeout_seconds=8,
            )
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
                    "evaluation_seed": evaluation_seed,
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
        "task_pack_version": selection.pack_version,
        "task_pack_source": selection.pack_source,
        "task_pack_hash": selection.pack_hash,
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
    write_outputs: bool = True,
    run_group_id: str | None = None,
) -> dict[str, Any]:
    if mentor_client is None and worker_client is None and client is None:
        client = OllamaClient()
    mentor_client = mentor_client or client
    worker_client = worker_client or client
    if mentor_client is None or worker_client is None:
        raise RuntimeError("Benchmark run is missing mentor or worker client initialization.")

    selection = resolve_tasks(
        task_pack=config.task_pack,
        task_pack_path=config.task_pack_path,
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
        max_turns=config.max_turns,
        seed=config.seed,
    )

    worker_template = _load_template("worker_prompt.txt")
    mentor_template = _load_template("mentor_prompt.txt")
    checkpoint_store = BenchmarkCheckpointStore(
        path=_checkpoint_path_for_results(config.results_path),
        metadata=_build_checkpoint_metadata(
            config=config,
            selection=selection,
            run_modes=run_modes,
            mentor_models=mentor_models,
            worker_models=worker_models,
            generation=generation,
            mentor_provider=mentor_provider,
            worker_provider=worker_provider,
        ),
    )
    loaded_from_checkpoint = 0
    appended_to_checkpoint = 0
    task_prompts = {
        task.task_id: read_task_prompt(task)
        for task in selected_tasks
    }

    runs: list[dict[str, Any]] = []
    baseline_lookup: dict[tuple[str, str], bool] = {}

    benchmark_start = time.perf_counter()

    def _load_completed_run(
        *,
        unit_key: RunUnitKey,
        task: Any,
    ) -> dict[str, Any] | None:
        nonlocal loaded_from_checkpoint
        existing = checkpoint_store.get_completed_run(unit_key)
        if existing is None:
            return None
        existing.setdefault("task_category", task.category)
        if str(existing.get("mode")) == "worker_only":
            baseline_lookup[(str(existing.get("worker_model")), str(existing.get("task_id")))] = bool(
                existing.get("pass")
            )
        elif "baseline_pass" not in existing:
            existing["baseline_pass"] = baseline_lookup.get(
                (str(existing.get("worker_model")), str(existing.get("task_id")))
            )
        runs.append(existing)
        loaded_from_checkpoint += 1
        return existing

    def _record_completed_run(
        *,
        unit_key: RunUnitKey,
        task: Any,
        run: dict[str, Any],
    ) -> None:
        nonlocal appended_to_checkpoint
        run.setdefault("task_category", task.category)
        if str(run.get("mode")) == "worker_only":
            baseline_lookup[(str(run.get("worker_model")), str(run.get("task_id")))] = bool(run.get("pass"))
        elif "baseline_pass" not in run:
            run["baseline_pass"] = baseline_lookup.get(
                (str(run.get("worker_model")), str(run.get("task_id")))
            )
        runs.append(run)
        checkpoint_store.record_completed_run(unit_key, run)
        appended_to_checkpoint += 1

    if run_worker_only:
        for worker_model in worker_models:
            for task in selected_tasks:
                unit_key = _run_unit_key(
                    seed=generation.seed,
                    mode="worker_only",
                    task_id=task.task_id,
                    worker_model=worker_model,
                    mentor_model=None,
                )
                if _load_completed_run(unit_key=unit_key, task=task) is not None:
                    continue
                temp_dir, workdir = materialize_task(task)
                try:
                    baseline = _baseline_run(
                        client=worker_client,
                        worker_model=worker_model,
                        task_prompt=task_prompts[task.task_id],
                        task_id=task.task_id,
                        task_family_id=task.family_id,
                        worker_template=worker_template,
                        workdir=workdir,
                        generation=generation,
                        test_timeout_seconds=config.test_timeout_seconds,
                        model_retry_attempts=config.model_retry_attempts,
                        model_retry_backoff_seconds=config.model_retry_backoff_seconds,
                    )
                    _record_completed_run(unit_key=unit_key, task=task, run=baseline)
                finally:
                    temp_dir.cleanup()

    if run_mentor_matrix:
        for mentor_model in mentor_models:
            for worker_model in worker_models:
                for task in selected_tasks:
                    unit_key = _run_unit_key(
                        seed=generation.seed,
                        mode="mentor_worker",
                        task_id=task.task_id,
                        worker_model=worker_model,
                        mentor_model=mentor_model,
                    )
                    if _load_completed_run(unit_key=unit_key, task=task) is not None:
                        continue
                    temp_dir, workdir = materialize_task(task)
                    try:
                        mentored = _mentored_run(
                            worker_client=worker_client,
                            mentor_client=mentor_client,
                            mentor_model=mentor_model,
                            worker_model=worker_model,
                            task_prompt=task_prompts[task.task_id],
                            task_id=task.task_id,
                            task_family_id=task.family_id,
                            worker_template=worker_template,
                            mentor_template=mentor_template,
                            workdir=workdir,
                            generation=generation,
                            mentor_strategy="real",
                            test_timeout_seconds=config.test_timeout_seconds,
                            model_retry_attempts=config.model_retry_attempts,
                            model_retry_backoff_seconds=config.model_retry_backoff_seconds,
                        )
                        mentored["baseline_pass"] = baseline_lookup.get((worker_model, task.task_id))
                        _record_completed_run(unit_key=unit_key, task=task, run=mentored)
                    finally:
                        temp_dir.cleanup()

    if run_control:
        for worker_model in worker_models:
            for task in selected_tasks:
                unit_key = _run_unit_key(
                    seed=generation.seed,
                    mode="mentor_only_suggestion_noise",
                    task_id=task.task_id,
                    worker_model=worker_model,
                    mentor_model="dummy_control",
                )
                if _load_completed_run(unit_key=unit_key, task=task) is not None:
                    continue
                temp_dir, workdir = materialize_task(task)
                try:
                    control = _mentored_run(
                        worker_client=worker_client,
                        mentor_client=mentor_client,
                        mentor_model="dummy_control",
                        worker_model=worker_model,
                        task_prompt=task_prompts[task.task_id],
                        task_id=task.task_id,
                        task_family_id=task.family_id,
                        worker_template=worker_template,
                        mentor_template=mentor_template,
                        workdir=workdir,
                        generation=generation,
                        mentor_strategy="dummy_control",
                        test_timeout_seconds=config.test_timeout_seconds,
                        model_retry_attempts=config.model_retry_attempts,
                        model_retry_backoff_seconds=config.model_retry_backoff_seconds,
                    )
                    control["baseline_pass"] = baseline_lookup.get((worker_model, task.task_id))
                    _record_completed_run(unit_key=unit_key, task=task, run=control)
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
        task_pack_id=selection.task_pack,
        task_pack_version=selection.pack_version,
        task_pack_source=selection.pack_source,
        task_pack_hash=selection.pack_hash,
        task_pack_manifest_path=selection.pack_manifest_path,
    )

    run_counts_by_mode: dict[str, int] = {}
    for run in runs:
        mode_name = str(run.get("mode"))
        run_counts_by_mode[mode_name] = run_counts_by_mode.get(mode_name, 0) + 1
    error_summary = _collect_run_error_summary(runs)
    accumulated_run_wall_time_seconds = round(
        sum(_safe_float(run.get("wall_time_seconds")) for run in runs),
        4,
    )
    compute_budget = _compute_budget_manifest(
        runs=runs,
        max_turns=generation.max_turns,
        model_timeout_seconds=config.timeout_seconds,
        test_timeout_seconds=config.test_timeout_seconds,
        total_wall_time_seconds=accumulated_run_wall_time_seconds,
    )
    integrity = _build_integrity_payload(runs)

    results = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "run_group_id": run_group_id,
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
            "timeout_seconds": config.timeout_seconds,
            "model_timeout_seconds": config.timeout_seconds,
            "test_timeout_seconds": config.test_timeout_seconds,
            "model_retry_attempts": config.model_retry_attempts,
            "model_retry_backoff_seconds": config.model_retry_backoff_seconds,
            "generation": {
                "temperature": generation.temperature,
                "top_p": generation.top_p,
                "worker_num_predict": generation.worker_num_predict,
                "mentor_num_predict": generation.mentor_num_predict,
                "seed": generation.seed,
            },
            "determinism": {
                "task_order_seed": int(config.seed),
                "prompt_seed_base": int(generation.seed),
                "evaluation_seed_base": int(_seed_for_call(generation.seed, "evaluation")),
                "pythonhashseed": 0,
            },
            "task_pack": selection.task_pack,
            "task_pack_version": selection.pack_version,
            "task_pack_source": selection.pack_source,
            "task_pack_license": selection.pack_license,
            "task_pack_hash": selection.pack_hash,
            "task_pack_manifest_path": selection.pack_manifest_path,
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
            "benchmark_wall_time_seconds": accumulated_run_wall_time_seconds,
            "violation_count": len(all_violations),
            "integrity_warning_count": len(integrity["warnings"]),
            "total_passes": int(error_summary["total_passes"]),
            "total_failed_runs": int(error_summary["total_failed_runs"]),
            "passes_by_mode": error_summary["passes_by_mode"],
            "failed_runs_by_mode": error_summary["failed_runs_by_mode"],
            "model_call_errors_by_mode": error_summary["model_call_errors_by_mode"],
            "model_call_timeouts_by_mode": error_summary["model_call_timeouts_by_mode"],
            "total_model_call_errors": int(error_summary["total_model_call_errors"]),
            "total_model_call_timeouts": int(error_summary["total_model_call_timeouts"]),
        },
        "compute_budget": compute_budget,
        "integrity": integrity,
        "checkpointing": {
            "enabled": True,
            "checkpoint_path": str(_checkpoint_path_for_results(config.results_path)),
            "completed_units_loaded": loaded_from_checkpoint,
            "completed_units_recorded": appended_to_checkpoint,
            "resumable_unit": "seed,mode,task_id,worker_model,mentor_model",
            "session_wall_time_seconds": round(elapsed, 4),
        },
        "runs": runs,
        "violations": all_violations,
        "aggregates": aggregates,
    }
    _attach_reproducibility_manifest(results)

    if write_outputs:
        config.results_path.parent.mkdir(parents=True, exist_ok=True)
        config.results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        write_leaderboard(results, config.results_path.parent / "leaderboard.md")
    return results


def _safe_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _collect_run_error_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    passes_by_mode: dict[str, int] = {}
    failed_runs_by_mode: dict[str, int] = {}
    model_call_errors_by_mode: dict[str, int] = {}
    model_call_timeouts_by_mode: dict[str, int] = {}
    total_passes = 0

    def _record_error(mode: str, message: Any) -> None:
        if not isinstance(message, str) or not message.strip():
            return
        model_call_errors_by_mode[mode] = model_call_errors_by_mode.get(mode, 0) + 1
        if TIMEOUT_TOKEN_RE.search(message):
            model_call_timeouts_by_mode[mode] = model_call_timeouts_by_mode.get(mode, 0) + 1

    for run in runs:
        mode = str(run.get("mode", "unknown"))
        if run.get("pass"):
            total_passes += 1
            passes_by_mode[mode] = passes_by_mode.get(mode, 0) + 1
            failed_runs_by_mode.setdefault(mode, 0)
        else:
            passes_by_mode.setdefault(mode, 0)
            failed_runs_by_mode[mode] = failed_runs_by_mode.get(mode, 0) + 1

        log = run.get("log", {})
        if not isinstance(log, dict):
            continue

        if mode == "worker_only":
            _record_error(mode, log.get("worker_error"))
            continue

        turns = log.get("turns", [])
        if not isinstance(turns, list):
            continue
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            _record_error(mode, turn.get("worker_error"))
            _record_error(mode, turn.get("mentor_error"))

    return {
        "total_passes": total_passes,
        "total_failed_runs": len(runs) - total_passes,
        "passes_by_mode": passes_by_mode,
        "failed_runs_by_mode": failed_runs_by_mode,
        "model_call_errors_by_mode": model_call_errors_by_mode,
        "model_call_timeouts_by_mode": model_call_timeouts_by_mode,
        "total_model_call_errors": sum(model_call_errors_by_mode.values()),
        "total_model_call_timeouts": sum(model_call_timeouts_by_mode.values()),
    }


def _detect_low_runtime_warning(runs: list[dict[str, Any]]) -> list[str]:
    runtimes: list[float] = []
    for run in runs:
        value = run.get("test_runtime_seconds")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        runtimes.append(float(value))

    if not runtimes:
        return []

    low_runtime_count = sum(1 for item in runtimes if item < 0.1)
    share = low_runtime_count / len(runtimes)
    if share > 0.8:
        return [
            (
                "tests may not be executing "
                f"(runtime <0.1s for {low_runtime_count}/{len(runtimes)} task runs)."
            )
        ]
    return []


def _detect_baseline_reuse_warning(runs: list[dict[str, Any]]) -> list[str]:
    worker_only_runs = [run for run in runs if str(run.get("mode")) == "worker_only"]
    if not worker_only_runs:
        return []

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for run in worker_only_runs:
        worker = str(run.get("worker_model", "unknown"))
        seed_raw = run.get("seed")
        if isinstance(seed_raw, bool) or not isinstance(seed_raw, (int, float)):
            seed = 0
        else:
            seed = int(seed_raw)
        grouped.setdefault((worker, seed), []).append(run)

    by_signature: dict[tuple[tuple[int, ...], tuple[str, ...]], list[tuple[str, int]]] = {}
    for key, items in grouped.items():
        ordered = sorted(items, key=lambda item: str(item.get("task_id", "")))
        baseline_vector = tuple(1 if bool(item.get("pass")) else 0 for item in ordered)
        patch_vector = tuple(str(item.get("patch_hash") or "") for item in ordered)
        signature = (baseline_vector, patch_vector)
        by_signature.setdefault(signature, []).append(key)

    warnings: list[str] = []
    for groups in by_signature.values():
        if len(groups) <= 1:
            continue
        labels = ", ".join(f"{worker}@seed{seed}" for worker, seed in sorted(groups))
        warnings.append(
            "potential artifact reuse detected: identical baseline vectors and patch hashes across "
            f"worker-only groups ({labels})."
        )
    return warnings


def _build_integrity_payload(runs: list[dict[str, Any]]) -> dict[str, Any]:
    runtime_warnings = _detect_low_runtime_warning(runs)
    baseline_warnings = _detect_baseline_reuse_warning(runs)
    warnings = runtime_warnings + baseline_warnings
    return {
        "warnings": warnings,
        "runtime_warnings": runtime_warnings,
        "baseline_reuse_warnings": baseline_warnings,
    }


def _count_model_calls_attempted_for_run(run: dict[str, Any]) -> int:
    mode = str(run.get("mode", ""))
    if mode == "worker_only":
        return 1

    log = run.get("log", {})
    if not isinstance(log, dict):
        return 0
    turns = log.get("turns", [])
    if not isinstance(turns, list):
        return 0

    calls = 0
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        worker_attempted = any(
            key in turn
            for key in ("worker_prompt", "worker_response", "worker_error", "extracted_patch")
        )
        if worker_attempted:
            calls += 1

        mentor_attempted = mode == "mentor_worker" and any(
            key in turn
            for key in ("mentor_prompt", "mentor_response_raw", "mentor_error", "mentor_guidance")
        )
        if mentor_attempted:
            calls += 1

    return calls


def _compute_budget_manifest(
    *,
    runs: list[dict[str, Any]],
    max_turns: int,
    model_timeout_seconds: int,
    test_timeout_seconds: int,
    total_wall_time_seconds: float,
) -> dict[str, Any]:
    calls_by_mode: dict[str, int] = {}
    total_calls = 0
    total_tokens = 0
    tokens_available = True

    for run in runs:
        mode = str(run.get("mode", "unknown"))
        attempted = _count_model_calls_attempted_for_run(run)
        calls_by_mode[mode] = calls_by_mode.get(mode, 0) + attempted
        total_calls += attempted

        token_value = run.get("total_tokens_estimate")
        if isinstance(token_value, bool) or not isinstance(token_value, (int, float)):
            tokens_available = False
        else:
            total_tokens += int(token_value)

    return {
        "max_turns": int(max_turns),
        "timeout_seconds": int(model_timeout_seconds),
        "model_timeout_seconds": int(model_timeout_seconds),
        "test_timeout_seconds": int(test_timeout_seconds),
        "total_model_calls_attempted": int(total_calls),
        "model_calls_attempted_by_mode": calls_by_mode,
        "total_tokens_estimate": int(total_tokens) if tokens_available else "unavailable",
        "total_wall_time_seconds": round(float(total_wall_time_seconds), 4),
    }


def _run_signature_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        seed_raw = run.get("seed")
        seed = int(seed_raw) if isinstance(seed_raw, (int, float)) and not isinstance(seed_raw, bool) else 0
        patch_hashes_raw = run.get("patch_hashes", [])
        patch_hashes = (
            [str(item) for item in patch_hashes_raw if isinstance(item, str)]
            if isinstance(patch_hashes_raw, list)
            else []
        )
        rows.append(
            {
                "seed": seed,
                "mode": str(run.get("mode", "")),
                "task_id": str(run.get("task_id", "")),
                "worker_model": str(run.get("worker_model", "")),
                "mentor_model": str(run.get("mentor_model", "")),
                "pass": bool(run.get("pass", False)),
                "turns_used": int(run.get("turns_used", 0) or 0),
                "tests_executed": int(run.get("tests_executed", 0) or 0),
                "tests_passed": int(run.get("tests_passed", 0) or 0),
                "tests_failed": int(run.get("tests_failed", 0) or 0),
                "patch_hash": str(run.get("patch_hash", "") or ""),
                "patch_hashes": patch_hashes,
            }
        )
    rows.sort(
        key=lambda row: (
            int(row["seed"]),
            str(row["mode"]),
            str(row["worker_model"]),
            str(row["mentor_model"]),
            str(row["task_id"]),
        )
    )
    return rows


def _deterministic_reproducibility_hash(results_payload: dict[str, Any]) -> str:
    config = results_payload.get("config", {})
    if not isinstance(config, dict):
        config = {}

    determinism = config.get("determinism", {})
    if not isinstance(determinism, dict):
        determinism = {}

    material = {
        "task_pack": config.get("task_pack"),
        "suite": config.get("suite"),
        "run_modes": config.get("run_modes"),
        "seed_list": config.get("seed_list"),
        "generation_seed": config.get("generation", {}).get("seed")
        if isinstance(config.get("generation"), dict)
        else None,
        "determinism": determinism,
        "runs": _run_signature_rows(results_payload.get("runs", []) if isinstance(results_payload.get("runs"), list) else []),
        "aggregates": results_payload.get("aggregates", {}),
    }
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _attach_reproducibility_manifest(results_payload: dict[str, Any]) -> None:
    config = results_payload.get("config", {})
    if not isinstance(config, dict):
        config = {}
    determinism = config.get("determinism", {})
    if not isinstance(determinism, dict):
        determinism = {}

    seed_list = config.get("seed_list")
    if isinstance(seed_list, list):
        normalized_seeds = [int(seed) for seed in seed_list if isinstance(seed, int)]
    else:
        generation = config.get("generation", {})
        seed = generation.get("seed") if isinstance(generation, dict) else None
        normalized_seeds = [int(seed)] if isinstance(seed, int) else []

    results_payload["reproducibility"] = {
        "seed_policy": "deterministic",
        "task_order_seed": determinism.get("task_order_seed"),
        "prompt_seed_base": determinism.get("prompt_seed_base"),
        "evaluation_seed_base": determinism.get("evaluation_seed_base"),
        "pythonhashseed": determinism.get("pythonhashseed"),
        "seed_list": normalized_seeds,
        "deterministic_output_sha256": _deterministic_reproducibility_hash(results_payload),
    }


def _merge_compute_budget(
    *,
    replicate_results: list[dict[str, Any]],
    max_turns: int,
    model_timeout_seconds: int,
    test_timeout_seconds: int,
) -> dict[str, Any]:
    total_calls = 0
    total_tokens = 0
    tokens_available = True
    total_wall_time = 0.0
    calls_by_mode: dict[str, int] = {}

    for replicate in replicate_results:
        budget = replicate.get("compute_budget", {})
        if not isinstance(budget, dict):
            budget = {}

        call_value = budget.get("total_model_calls_attempted")
        if isinstance(call_value, bool) or not isinstance(call_value, (int, float)):
            call_value = _compute_budget_manifest(
                runs=replicate.get("runs", []) if isinstance(replicate.get("runs"), list) else [],
                max_turns=max_turns,
                model_timeout_seconds=model_timeout_seconds,
                test_timeout_seconds=test_timeout_seconds,
                total_wall_time_seconds=0.0,
            )["total_model_calls_attempted"]
        total_calls += int(call_value)

        tokens_value = budget.get("total_tokens_estimate")
        if isinstance(tokens_value, str) and tokens_value == "unavailable":
            tokens_available = False
        elif isinstance(tokens_value, bool) or not isinstance(tokens_value, (int, float)):
            tokens_available = False
        else:
            total_tokens += int(tokens_value)

        wall = budget.get("total_wall_time_seconds")
        if isinstance(wall, bool) or not isinstance(wall, (int, float)):
            wall = replicate.get("summary", {}).get("benchmark_wall_time_seconds", 0.0)
        if isinstance(wall, (int, float)) and not isinstance(wall, bool):
            total_wall_time += float(wall)

        by_mode = budget.get("model_calls_attempted_by_mode")
        if isinstance(by_mode, dict):
            for mode, count in by_mode.items():
                if not isinstance(mode, str):
                    continue
                if isinstance(count, bool) or not isinstance(count, (int, float)):
                    continue
                calls_by_mode[mode] = calls_by_mode.get(mode, 0) + int(count)

    return {
        "max_turns": int(max_turns),
        "timeout_seconds": int(model_timeout_seconds),
        "model_timeout_seconds": int(model_timeout_seconds),
        "test_timeout_seconds": int(test_timeout_seconds),
        "total_model_calls_attempted": int(total_calls),
        "model_calls_attempted_by_mode": calls_by_mode,
        "total_tokens_estimate": int(total_tokens) if tokens_available else "unavailable",
        "total_wall_time_seconds": round(total_wall_time, 4),
        "replicate_count": len(replicate_results),
    }


def _combine_replicate_results(
    *,
    config: BenchmarkConfig,
    replicate_results: list[dict[str, Any]],
    seeds: list[int],
    run_group_id: str,
) -> dict[str, Any]:
    if not replicate_results:
        raise RuntimeError("No replicate results to combine.")

    first = replicate_results[0]
    first_config = first.get("config", {}) if isinstance(first.get("config"), dict) else {}
    run_modes = _normalize_run_modes(
        list(first_config.get("run_modes", []))
        if isinstance(first_config.get("run_modes"), list)
        else list(config.run_modes)
    )
    merged_runs: list[dict[str, Any]] = []
    merged_violations: list[dict[str, Any]] = []
    replicate_payloads: list[dict[str, Any]] = []

    for index, (seed, replicate) in enumerate(zip(seeds, replicate_results), start=1):
        runs = replicate.get("runs", [])
        if isinstance(runs, list):
            merged_runs.extend(runs)

        violations = replicate.get("violations", [])
        if isinstance(violations, list):
            merged_violations.extend(violations)

        replicate_payloads.append(
            {
                "replicate_id": f"seed_{seed}",
                "seed": int(seed),
                "run_group_id": run_group_id,
                "generated_at": str(replicate.get("generated_at", "")),
                "config": replicate.get("config", {}),
                "summary": replicate.get("summary", {}),
                "compute_budget": replicate.get("compute_budget", {}),
                "runs": runs if isinstance(runs, list) else [],
            }
        )

    run_counts_by_mode: dict[str, int] = {}
    for run in merged_runs:
        mode_name = str(run.get("mode", "unknown"))
        run_counts_by_mode[mode_name] = run_counts_by_mode.get(mode_name, 0) + 1

    error_summary = _collect_run_error_summary(merged_runs)
    integrity = _build_integrity_payload(merged_runs)
    max_turns_raw = first_config.get("max_turns", config.max_turns)
    model_timeout_raw = first_config.get("model_timeout_seconds", first_config.get("timeout_seconds", config.timeout_seconds))
    test_timeout_raw = first_config.get("test_timeout_seconds", config.test_timeout_seconds)
    max_turns = int(max_turns_raw) if isinstance(max_turns_raw, (int, float)) else int(config.max_turns)
    model_timeout_seconds = (
        int(model_timeout_raw)
        if isinstance(model_timeout_raw, (int, float))
        else int(config.timeout_seconds)
    )
    test_timeout_seconds = (
        int(test_timeout_raw)
        if isinstance(test_timeout_raw, (int, float))
        else int(config.test_timeout_seconds)
    )
    compute_budget = _merge_compute_budget(
        replicate_results=replicate_results,
        max_turns=max_turns,
        model_timeout_seconds=model_timeout_seconds,
        test_timeout_seconds=test_timeout_seconds,
    )
    worker_models = (
        [str(item) for item in first_config.get("worker_models", []) if isinstance(item, str)]
        if isinstance(first_config.get("worker_models"), list)
        else []
    )
    mentor_models = (
        [str(item) for item in first_config.get("mentor_models", []) if isinstance(item, str)]
        if isinstance(first_config.get("mentor_models"), list)
        else []
    )
    if not mentor_models:
        mentor_models = worker_models

    task_categories: dict[str, str] = {}
    for run in merged_runs:
        if not isinstance(run, dict):
            continue
        task_id = run.get("task_id")
        task_category = run.get("task_category")
        if isinstance(task_id, str) and task_id and isinstance(task_category, str) and task_category:
            task_categories[task_id] = task_category

    merged_aggregates = _compute_aggregates(
        runs=merged_runs,
        worker_models=worker_models,
        mentor_models=mentor_models,
        task_categories=task_categories,
    )

    merged = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "run_group_id": run_group_id,
        "config": {
            **first_config,
            "run_group_id": run_group_id,
            "seed_list": [int(seed) for seed in seeds],
            "seed_count": len(seeds),
            "determinism": {
                **(
                    first_config.get("determinism", {})
                    if isinstance(first_config.get("determinism"), dict)
                    else {}
                ),
                "seed_list": [int(seed) for seed in seeds],
                "seed_count": len(seeds),
            },
            "run_modes": run_modes,
        },
        "environment": first.get("environment", {}),
        "summary": {
            "total_runs": len(merged_runs),
            "runs_by_mode": run_counts_by_mode,
            "benchmark_wall_time_seconds": compute_budget["total_wall_time_seconds"],
            "violation_count": len(merged_violations),
            "integrity_warning_count": len(integrity["warnings"]),
            "total_passes": int(error_summary["total_passes"]),
            "total_failed_runs": int(error_summary["total_failed_runs"]),
            "passes_by_mode": error_summary["passes_by_mode"],
            "failed_runs_by_mode": error_summary["failed_runs_by_mode"],
            "model_call_errors_by_mode": error_summary["model_call_errors_by_mode"],
            "model_call_timeouts_by_mode": error_summary["model_call_timeouts_by_mode"],
            "total_model_call_errors": int(error_summary["total_model_call_errors"]),
            "total_model_call_timeouts": int(error_summary["total_model_call_timeouts"]),
            "replicate_count": len(seeds),
        },
        "compute_budget": compute_budget,
        "integrity": integrity,
        "runs": merged_runs,
        "violations": merged_violations,
        "aggregates": merged_aggregates,
        "replicates": replicate_payloads,
    }
    return merged


def run_multi_seed_benchmark(
    config: BenchmarkConfig,
    *,
    seeds: list[int],
    client: LLMClient | None = None,
    mentor_client: LLMClient | None = None,
    worker_client: LLMClient | None = None,
) -> dict[str, Any]:
    if not seeds:
        raise ValueError("`seeds` must contain at least one seed.")
    if len(set(seeds)) != len(seeds):
        raise ValueError("`seeds` must not contain duplicates.")

    if len(seeds) == 1:
        return run_benchmark(
            replace(config, seed=int(seeds[0])),
            client=client,
            mentor_client=mentor_client,
            worker_client=worker_client,
        )

    effective_max_turns = config.max_turns
    effective_worker_num_predict = config.worker_num_predict_override or REPRO_WORKER_MAX_TOKENS
    effective_mentor_num_predict = config.mentor_num_predict_override or REPRO_MENTOR_MAX_TOKENS
    run_group_id = deterministic_run_group_id(
        task_pack=config.task_pack,
        suite=config.suite or "explicit",
        run_modes=_normalize_run_modes(list(config.run_modes)),
        mentor_models=list(config.mentor_models_override or config.models),
        worker_models=list(config.worker_models_override or config.models),
        provider=config.provider,
        mentor_provider=(config.mentor_provider or config.provider),
        worker_provider=(config.worker_provider or config.provider),
        max_turns=effective_max_turns,
        timeout_seconds=config.timeout_seconds,
        repro_mode=config.repro_mode,
        worker_num_predict=effective_worker_num_predict,
        mentor_num_predict=effective_mentor_num_predict,
        seeds=[int(seed) for seed in seeds],
    )

    replicate_results: list[dict[str, Any]] = []
    for seed in seeds:
        seed_results_path = _seed_results_path(config.results_path, int(seed))
        replicate = run_benchmark(
            replace(config, seed=int(seed), results_path=seed_results_path),
            client=client,
            mentor_client=mentor_client,
            worker_client=worker_client,
            write_outputs=False,
            run_group_id=run_group_id,
        )
        seed_results_path.parent.mkdir(parents=True, exist_ok=True)
        seed_results_path.write_text(json.dumps(replicate, indent=2), encoding="utf-8")
        replicate_results.append(replicate)

    merged = _combine_replicate_results(
        config=config,
        replicate_results=replicate_results,
        seeds=[int(seed) for seed in seeds],
        run_group_id=run_group_id,
    )
    _attach_reproducibility_manifest(merged)

    config.results_path.parent.mkdir(parents=True, exist_ok=True)
    config.results_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    write_leaderboard(merged, config.results_path.parent / "leaderboard.md")
    return merged


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
