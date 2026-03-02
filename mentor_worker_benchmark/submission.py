from __future__ import annotations

import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mentor_worker_benchmark import __version__

REQUIRED_SUBMISSION_FILES = ("results.json", "environment.json", "submission_manifest.json")
GIT_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _expect_type(
    obj: dict[str, Any],
    key: str,
    expected_type: type[Any] | tuple[type[Any], ...],
    path: str,
    errors: list[str],
) -> Any:
    if key not in obj:
        errors.append(f"Missing required field: {path}.{key}")
        return None
    value = obj[key]
    if not isinstance(value, expected_type):
        if isinstance(expected_type, tuple):
            expected_label = "|".join(item.__name__ for item in expected_type)
        else:
            expected_label = expected_type.__name__
        errors.append(
            f"Invalid type for {path}.{key}: expected {expected_label}, got {type(value).__name__}"
        )
        return None
    return value


def validate_results_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if not isinstance(payload, dict):
        return ["results.json must contain a JSON object"]

    config = _expect_type(payload, "config", dict, "results", errors)
    environment = _expect_type(payload, "environment", dict, "results", errors)
    summary = _expect_type(payload, "summary", dict, "results", errors)
    runs = _expect_type(payload, "runs", list, "results", errors)
    aggregates = _expect_type(payload, "aggregates", dict, "results", errors)
    _expect_type(payload, "generated_at", str, "results", errors)

    if isinstance(config, dict):
        _expect_type(config, "task_pack", str, "results.config", errors)
        _expect_type(config, "suite", str, "results.config", errors)
        _expect_type(config, "run_modes", list, "results.config", errors)
        _expect_type(config, "models", list, "results.config", errors)
        _expect_type(config, "worker_models", list, "results.config", errors)
        _expect_type(config, "generation", dict, "results.config", errors)

    if isinstance(environment, dict):
        git = _expect_type(environment, "git", dict, "results.environment", errors)
        _expect_type(environment, "python", dict, "results.environment", errors)
        _expect_type(environment, "platform", dict, "results.environment", errors)
        _expect_type(environment, "ollama", dict, "results.environment", errors)
        if isinstance(git, dict):
            commit = _expect_type(git, "commit", str, "results.environment.git", errors)
            if isinstance(commit, str) and not commit.strip():
                errors.append("results.environment.git.commit cannot be empty")

    if isinstance(summary, dict):
        total_runs = _expect_type(summary, "total_runs", int, "results.summary", errors)
        _expect_type(summary, "runs_by_mode", dict, "results.summary", errors)
        _expect_type(summary, "benchmark_wall_time_seconds", (int, float), "results.summary", errors)
        _expect_type(summary, "violation_count", int, "results.summary", errors)
        if isinstance(total_runs, int) and isinstance(runs, list) and total_runs != len(runs):
            errors.append(
                f"results.summary.total_runs ({total_runs}) does not match len(results.runs) ({len(runs)})"
            )

    if isinstance(runs, list):
        for index, row in enumerate(runs):
            if not isinstance(row, dict):
                errors.append(f"results.runs[{index}] must be an object")
                continue
            path = f"results.runs[{index}]"
            _expect_type(row, "mode", str, path, errors)
            _expect_type(row, "task_id", str, path, errors)
            _expect_type(row, "worker_model", str, path, errors)
            _expect_type(row, "pass", bool, path, errors)
            _expect_type(row, "turns_used", int, path, errors)
            _expect_type(row, "wall_time_seconds", (int, float), path, errors)
            _expect_type(row, "total_tokens_estimate", int, path, errors)
            _expect_type(row, "log", dict, path, errors)

    if isinstance(aggregates, dict):
        _expect_type(aggregates, "task_count", int, "results.aggregates", errors)
        _expect_type(aggregates, "tasks", list, "results.aggregates", errors)
        _expect_type(aggregates, "best_mentors", list, "results.aggregates", errors)
        _expect_type(aggregates, "best_workers", list, "results.aggregates", errors)
        _expect_type(aggregates, "mentor_worker_pairs", list, "results.aggregates", errors)

    return errors


def _task_pack_root(task_pack: str) -> Path:
    return Path(__file__).resolve().parent / "tasks" / task_pack


def resolve_task_pack_version(task_pack: str) -> str | None:
    metadata_path = _task_pack_root(task_pack) / "metadata.json"
    if not metadata_path.exists():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    value = payload.get("pack_version")
    return str(value) if isinstance(value, (str, int, float)) else None


def _infer_cli_command(results_payload: dict[str, Any]) -> str:
    config = results_payload.get("config", {})
    generation = config.get("generation", {}) if isinstance(config, dict) else {}

    models = config.get("models", [])
    mentor_models = config.get("mentor_models", models)
    worker_models = config.get("worker_models", models)
    provider = str(config.get("provider", "ollama"))
    mentor_provider = str(config.get("mentor_provider", provider))
    worker_provider = str(config.get("worker_provider", provider))
    run_modes = config.get("run_modes", [])
    seed = generation.get("seed", 1337)
    max_turns = config.get("max_turns", 4)
    suite = config.get("suite", "dev,test")
    task_pack = config.get("task_pack", "task_pack_v2")
    repro = bool(config.get("repro_mode", False))

    command = [
        "python -m mentor_worker_benchmark run",
        f"--task-pack {task_pack}",
        f"--suite {suite}",
        f"--models {','.join(str(item) for item in models) if models else 'default'}",
        f"--run-modes {','.join(str(item) for item in run_modes) if run_modes else 'default'}",
        f"--seed {seed}",
        f"--max-turns {max_turns}",
        "--results-path results/results.json",
    ]
    if provider:
        command.append(f"--provider {provider}")
    if mentor_provider and mentor_provider != provider:
        command.append(f"--mentor-provider {mentor_provider}")
    if worker_provider and worker_provider != provider:
        command.append(f"--worker-provider {worker_provider}")
    if isinstance(mentor_models, list) and mentor_models and mentor_models != models:
        command.append(f"--mentor-models {','.join(str(item) for item in mentor_models)}")
    if isinstance(worker_models, list) and worker_models and worker_models != models:
        command.append(f"--worker-models {','.join(str(item) for item in worker_models)}")
    if repro:
        command.append("--repro")
    return " ".join(command)


def _resolve_export_commit_hash() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "Unable to resolve git commit hash at export time via `git rev-parse HEAD`."
        ) from exc

    commit_hash = process.stdout.strip()
    if not GIT_HASH_RE.fullmatch(commit_hash):
        raise RuntimeError(f"Resolved git commit hash has invalid format: {commit_hash}")
    return commit_hash


def export_submission_bundle(
    *,
    results_path: Path,
    out_path: Path,
    cli_command: str | None = None,
    official_submission: bool = False,
) -> dict[str, Any]:
    if not results_path.exists():
        raise RuntimeError(f"Results file not found: {results_path}")

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    result_errors = validate_results_payload(payload)
    if result_errors:
        joined = "\n".join(f"- {item}" for item in result_errors)
        raise RuntimeError(f"results.json failed validation:\n{joined}")

    config = payload["config"]
    commit_hash = _resolve_export_commit_hash()

    # Capture export-time commit hash in both results payload and environment artifact.
    payload_for_bundle = json.loads(json.dumps(payload))
    environment = payload_for_bundle.get("environment", {})
    if not isinstance(environment, dict):
        environment = {}
    git = environment.get("git", {})
    if not isinstance(git, dict):
        git = {}
    git["commit"] = commit_hash
    environment["git"] = git
    payload_for_bundle["environment"] = environment

    task_pack = str(config["task_pack"])
    task_pack_version = resolve_task_pack_version(task_pack)
    if not task_pack_version:
        raise RuntimeError(
            f"Task pack `{task_pack}` not found locally (missing metadata.json in mentor_worker_benchmark/tasks)."
        )

    inferred_command = _infer_cli_command(payload)
    command_used = cli_command.strip() if isinstance(cli_command, str) and cli_command.strip() else inferred_command

    manifest = {
        "bundle_version": "1",
        "created_at": datetime.now(UTC).isoformat(),
        "tool_version": __version__,
        "results_filename": "results.json",
        "environment_filename": "environment.json",
        "task_pack": task_pack,
        "task_pack_version": task_pack_version,
        "git_commit_hash": commit_hash,
        "cli_command": command_used,
        "official_submission": bool(official_submission),
        "source_results_path": str(results_path),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload_for_bundle, indent=2))
        archive.writestr("environment.json", json.dumps(environment, indent=2))
        archive.writestr("submission_manifest.json", json.dumps(manifest, indent=2))

    return manifest


def read_submission_bundle(submission_path: Path) -> dict[str, Any]:
    if not submission_path.exists():
        raise RuntimeError(f"Submission file not found: {submission_path}")

    try:
        with zipfile.ZipFile(submission_path, "r") as archive:
            names = set(archive.namelist())
            missing = [required for required in REQUIRED_SUBMISSION_FILES if required not in names]
            if missing:
                missing_label = ", ".join(missing)
                raise RuntimeError(f"Missing required archive file(s): {missing_label}")

            results_payload = json.loads(archive.read("results.json").decode("utf-8"))
            environment_payload = json.loads(archive.read("environment.json").decode("utf-8"))
            manifest_payload = json.loads(archive.read("submission_manifest.json").decode("utf-8"))
    except zipfile.BadZipFile:
        raise RuntimeError(f"Invalid zip archive: {submission_path}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in submission archive: {exc}") from exc

    return {
        "submission_path": str(submission_path),
        "results": results_payload,
        "environment": environment_payload,
        "manifest": manifest_payload,
    }


def verify_submission_bundle(submission_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    details: dict[str, Any] = {"submission_path": str(submission_path)}

    try:
        bundle = read_submission_bundle(submission_path)
    except RuntimeError as exc:
        return {"ok": False, "errors": [str(exc)], "details": details}

    results_payload = bundle["results"]
    environment_payload = bundle["environment"]
    manifest_payload = bundle["manifest"]

    result_errors = validate_results_payload(results_payload)
    errors.extend(result_errors)

    if results_payload.get("environment") != environment_payload:
        errors.append("environment.json does not match results.environment payload")

    if not isinstance(manifest_payload, dict):
        errors.append("submission_manifest.json must contain a JSON object")
    else:
        manifest = manifest_payload
        for key in (
            "bundle_version",
            "task_pack",
            "task_pack_version",
            "git_commit_hash",
            "cli_command",
        ):
            if key not in manifest:
                errors.append(f"Missing required manifest field: {key}")

        task_pack = str(manifest.get("task_pack", "")).strip()
        task_pack_version = str(manifest.get("task_pack_version", "")).strip()
        commit_hash = str(manifest.get("git_commit_hash", "")).strip()
        cli_command = str(manifest.get("cli_command", "")).strip()

        if not task_pack:
            errors.append("Manifest task_pack cannot be empty")
        if not task_pack_version:
            errors.append("Manifest task_pack_version cannot be empty")
        if not commit_hash:
            errors.append("Manifest git_commit_hash cannot be empty")
        elif not GIT_HASH_RE.fullmatch(commit_hash):
            errors.append(f"Manifest git_commit_hash has invalid format: {commit_hash}")
        if not cli_command:
            errors.append("Manifest cli_command cannot be empty")
        official_submission = manifest.get("official_submission")
        if official_submission is not None and not isinstance(official_submission, bool):
            errors.append("Manifest official_submission must be a boolean when present")

        if task_pack:
            discovered_version = resolve_task_pack_version(task_pack)
            if not discovered_version:
                errors.append(f"Task pack `{task_pack}` does not exist locally.")
            elif task_pack_version and task_pack_version != discovered_version:
                errors.append(
                    f"Manifest task_pack_version mismatch: bundle={task_pack_version}, local={discovered_version}"
                )

        results_task_pack = str(results_payload.get("config", {}).get("task_pack", "")).strip()
        if task_pack and results_task_pack and task_pack != results_task_pack:
            errors.append(
                f"Task pack mismatch between manifest (`{task_pack}`) and results (`{results_task_pack}`)."
            )

        results_commit = str(
            results_payload.get("environment", {}).get("git", {}).get("commit", "")
        ).strip()
        if results_commit and commit_hash and results_commit != commit_hash:
            errors.append(
                f"Commit hash mismatch between manifest (`{commit_hash}`) and results (`{results_commit}`)."
            )

        details["task_pack"] = task_pack
        details["task_pack_version"] = task_pack_version
        details["git_commit_hash"] = commit_hash
        details["cli_command"] = cli_command
        details["official_submission"] = bool(official_submission)

    return {"ok": len(errors) == 0, "errors": errors, "details": details}


def render_verification_report(report: dict[str, Any]) -> str:
    if report.get("ok"):
        details = report.get("details", {})
        lines = [
            "Submission verification passed.",
            f"- Submission: {details.get('submission_path')}",
            f"- Task pack: {details.get('task_pack')} ({details.get('task_pack_version')})",
            f"- Commit: {details.get('git_commit_hash')}",
            f"- Label: {'official' if details.get('official_submission') else 'community (not official)'}",
            f"- Command: {details.get('cli_command')}",
        ]
        return "\n".join(lines)

    lines = ["Submission verification failed."]
    for error in report.get("errors", []):
        lines.append(f"- {error}")
    return "\n".join(lines)
