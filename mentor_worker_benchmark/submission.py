from __future__ import annotations

import json
import re
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mentor_worker_benchmark import __version__
from mentor_worker_benchmark.analysis import (
    analysis_required_for_results,
    generate_analysis_payload,
    validate_analysis_payload,
)
from mentor_worker_benchmark.protocol import (
    OFFICIAL_HEADLINE_SEEDS,
    OFFICIAL_PROTOCOL_VERSION,
    is_headline_suite,
    protocol_token,
    seed_token,
)

REQUIRED_SUBMISSION_FILES = ("results.json", "environment.json", "submission_manifest.json")
GIT_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    run_group_id = payload.get("run_group_id")
    if run_group_id is not None and not isinstance(run_group_id, str):
        errors.append("results.run_group_id must be a string when present")
    replicates = payload.get("replicates")
    if replicates is not None and not isinstance(replicates, list):
        errors.append("results.replicates must be a list when present")
    compute_budget = payload.get("compute_budget")
    if compute_budget is not None:
        _validate_compute_budget_manifest(
            budget=compute_budget,
            path="results.compute_budget",
            errors=errors,
        )

    if isinstance(config, dict):
        _expect_type(config, "task_pack", str, "results.config", errors)
        _expect_type(config, "suite", str, "results.config", errors)
        _expect_type(config, "run_modes", list, "results.config", errors)
        _expect_type(config, "models", list, "results.config", errors)
        _expect_type(config, "worker_models", list, "results.config", errors)
        _expect_type(config, "generation", dict, "results.config", errors)
        timeout_seconds = config.get("timeout_seconds")
        if timeout_seconds is not None and not isinstance(timeout_seconds, int):
            errors.append("results.config.timeout_seconds must be an integer when present")
        task_pack_version = config.get("task_pack_version")
        if task_pack_version is not None and not isinstance(task_pack_version, str):
            errors.append("results.config.task_pack_version must be a string when present")
        task_pack_source = config.get("task_pack_source")
        if task_pack_source is not None and not isinstance(task_pack_source, str):
            errors.append("results.config.task_pack_source must be a string when present")
        task_pack_hash = config.get("task_pack_hash")
        if task_pack_hash is not None and not isinstance(task_pack_hash, str):
            errors.append("results.config.task_pack_hash must be a string when present")

    if isinstance(environment, dict):
        git = _expect_type(environment, "git", dict, "results.environment", errors)
        python_env = _expect_type(environment, "python", dict, "results.environment", errors)
        _expect_type(environment, "platform", dict, "results.environment", errors)
        _expect_type(environment, "ollama", dict, "results.environment", errors)
        if isinstance(git, dict):
            commit = _expect_type(git, "commit", str, "results.environment.git", errors)
            if isinstance(commit, str) and not commit.strip():
                errors.append("results.environment.git.commit cannot be empty")
        if isinstance(python_env, dict):
            pip_freeze_hash = python_env.get("pip_freeze_sha256")
            if pip_freeze_hash is not None:
                if not isinstance(pip_freeze_hash, str):
                    errors.append(
                        "results.environment.python.pip_freeze_sha256 must be a string when present"
                    )
                elif pip_freeze_hash != "unavailable" and not SHA256_RE.fullmatch(pip_freeze_hash):
                    errors.append(
                        "results.environment.python.pip_freeze_sha256 must be a SHA256 hex digest "
                        "or `unavailable`"
                    )
            pip_freeze_count = python_env.get("pip_freeze_line_count")
            if pip_freeze_count is not None and (
                isinstance(pip_freeze_count, bool) or not isinstance(pip_freeze_count, int)
            ):
                errors.append(
                    "results.environment.python.pip_freeze_line_count must be an integer when present"
                )
        task_pack_env = environment.get("task_pack")
        if task_pack_env is not None:
            if not isinstance(task_pack_env, dict):
                errors.append("results.environment.task_pack must be an object when present")
            else:
                pack_id = task_pack_env.get("id")
                if pack_id is not None and not isinstance(pack_id, str):
                    errors.append("results.environment.task_pack.id must be a string when present")
                pack_source = task_pack_env.get("source")
                if pack_source is not None and not isinstance(pack_source, str):
                    errors.append("results.environment.task_pack.source must be a string when present")
                pack_hash = task_pack_env.get("hash")
                if pack_hash is not None:
                    if not isinstance(pack_hash, str):
                        errors.append("results.environment.task_pack.hash must be a string when present")
                    elif pack_hash and not SHA256_RE.fullmatch(pack_hash):
                        errors.append(
                            "results.environment.task_pack.hash must be a SHA256 hex digest when non-empty"
                        )

    if isinstance(summary, dict):
        total_runs = _expect_type(summary, "total_runs", int, "results.summary", errors)
        _expect_type(summary, "runs_by_mode", dict, "results.summary", errors)
        _expect_type(summary, "benchmark_wall_time_seconds", (int, float), "results.summary", errors)
        _expect_type(summary, "violation_count", int, "results.summary", errors)
        total_failed_runs = summary.get("total_failed_runs")
        if total_failed_runs is not None and not isinstance(total_failed_runs, int):
            errors.append("results.summary.total_failed_runs must be an integer when present")
        failed_runs_by_mode = summary.get("failed_runs_by_mode")
        if failed_runs_by_mode is not None and not isinstance(failed_runs_by_mode, dict):
            errors.append("results.summary.failed_runs_by_mode must be an object when present")
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

    if isinstance(replicates, list):
        for index, replicate in enumerate(replicates):
            if not isinstance(replicate, dict):
                errors.append(f"results.replicates[{index}] must be an object")
                continue
            path = f"results.replicates[{index}]"
            replicate_config = _expect_type(replicate, "config", dict, path, errors)
            replicate_runs = _expect_type(replicate, "runs", list, path, errors)
            replicate_budget = replicate.get("compute_budget")
            if replicate_budget is not None:
                _validate_compute_budget_manifest(
                    budget=replicate_budget,
                    path=f"{path}.compute_budget",
                    errors=errors,
                )
            if isinstance(replicate_config, dict):
                _expect_type(replicate_config, "task_pack", str, f"{path}.config", errors)
                _expect_type(replicate_config, "suite", str, f"{path}.config", errors)
                _expect_type(replicate_config, "run_modes", list, f"{path}.config", errors)
                _expect_type(replicate_config, "generation", dict, f"{path}.config", errors)
            if isinstance(replicate_runs, list):
                for run_index, row in enumerate(replicate_runs):
                    if not isinstance(row, dict):
                        errors.append(f"{path}.runs[{run_index}] must be an object")
                        continue
                    run_path = f"{path}.runs[{run_index}]"
                    _expect_type(row, "mode", str, run_path, errors)
                    _expect_type(row, "task_id", str, run_path, errors)
                    _expect_type(row, "worker_model", str, run_path, errors)
                    _expect_type(row, "pass", bool, run_path, errors)

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
    task_pack_source = str(config.get("task_pack_source", "builtin"))
    task_pack_manifest_path = str(config.get("task_pack_manifest_path", ""))
    repro = bool(config.get("repro_mode", False))
    timeout_seconds = config.get("timeout_seconds", 180)

    command = [
        "python -m mentor_worker_benchmark run",
        f"--task-pack {task_pack}",
        f"--suite {suite}",
        f"--models {','.join(str(item) for item in models) if models else 'default'}",
        f"--run-modes {','.join(str(item) for item in run_modes) if run_modes else 'default'}",
        f"--seed {seed}",
        f"--max-turns {max_turns}",
        f"--timeout {timeout_seconds}",
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
    if task_pack_source == "external" and task_pack_manifest_path:
        manifest_parent = Path(task_pack_manifest_path).parent
        command.append(f"--task-pack-path {manifest_parent}")
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


def _resolve_task_pack_version_for_export(config: dict[str, Any]) -> tuple[str, str]:
    task_pack = str(config.get("task_pack", ""))
    config_version = str(config.get("task_pack_version", "")).strip()
    pack_source = str(config.get("task_pack_source", "builtin")).strip().lower() or "builtin"

    if pack_source == "external":
        if not config_version:
            raise RuntimeError(
                "External task packs must include config.task_pack_version in results payload."
            )
        return config_version, pack_source

    discovered = resolve_task_pack_version(task_pack)
    if discovered:
        return discovered, pack_source
    if config_version:
        return config_version, pack_source
    raise RuntimeError(
        f"Task pack `{task_pack}` not found locally and no task_pack_version was present in results config."
    )


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _extract_protocol_seeds(payload: dict[str, Any]) -> list[int]:
    seeds: list[int] = []
    replicates = payload.get("replicates")
    if isinstance(replicates, list) and replicates:
        for replicate in replicates:
            if not isinstance(replicate, dict):
                continue
            seed = _safe_int(replicate.get("seed"))
            if seed is None:
                config = replicate.get("config", {})
                if isinstance(config, dict):
                    generation = config.get("generation", {})
                    if isinstance(generation, dict):
                        seed = _safe_int(generation.get("seed"))
            if seed is not None:
                seeds.append(seed)
        return seeds

    config = payload.get("config", {})
    if isinstance(config, dict):
        generation = config.get("generation", {})
        if isinstance(generation, dict):
            seed = _safe_int(generation.get("seed"))
            if seed is not None:
                return [seed]
        seed = _safe_int(config.get("seed"))
        if seed is not None:
            return [seed]
    return []


def _extract_compute_budget(payload: dict[str, Any]) -> dict[str, Any]:
    budget = payload.get("compute_budget")
    if isinstance(budget, dict):
        return budget
    return {}


def _normalize_compute_budget_for_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    budget = _extract_compute_budget(payload)
    summary = payload.get("summary", {})
    config = payload.get("config", {})

    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(config, dict):
        config = {}

    max_turns = _safe_int(budget.get("max_turns"))
    if max_turns is None:
        max_turns = _safe_int(config.get("max_turns"))
    timeout_seconds = _safe_int(budget.get("timeout_seconds"))
    if timeout_seconds is None:
        timeout_seconds = _safe_int(config.get("timeout_seconds"))

    total_calls = _safe_int(budget.get("total_model_calls_attempted"))
    if total_calls is None:
        total_calls = 0

    total_tokens = budget.get("total_tokens_estimate", "unavailable")
    if isinstance(total_tokens, bool) or not isinstance(total_tokens, (int, float, str)):
        total_tokens = "unavailable"
    if isinstance(total_tokens, str) and total_tokens != "unavailable":
        total_tokens = "unavailable"
    if isinstance(total_tokens, (int, float)) and not isinstance(total_tokens, bool):
        total_tokens = int(total_tokens)

    wall = budget.get("total_wall_time_seconds")
    if isinstance(wall, bool) or not isinstance(wall, (int, float)):
        wall = summary.get("benchmark_wall_time_seconds", 0.0)
    wall_value = float(wall) if isinstance(wall, (int, float)) and not isinstance(wall, bool) else 0.0

    return {
        "max_turns": int(max_turns) if max_turns is not None else 0,
        "timeout_seconds": int(timeout_seconds) if timeout_seconds is not None else 0,
        "total_model_calls_attempted": int(total_calls),
        "total_tokens_estimate": total_tokens,
        "total_wall_time_seconds": round(wall_value, 4),
    }


def _validate_compute_budget_manifest(
    *,
    budget: Any,
    path: str,
    errors: list[str],
) -> None:
    if not isinstance(budget, dict):
        errors.append(f"{path} must be an object")
        return

    for key in ("max_turns", "timeout_seconds", "total_model_calls_attempted"):
        value = budget.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{path}.{key} must be an integer")

    token_value = budget.get("total_tokens_estimate")
    if isinstance(token_value, str):
        if token_value != "unavailable":
            errors.append(f"{path}.total_tokens_estimate string value must be `unavailable`")
    elif isinstance(token_value, bool) or not isinstance(token_value, int):
        errors.append(f"{path}.total_tokens_estimate must be an integer or `unavailable`")

    wall_time = budget.get("total_wall_time_seconds")
    if isinstance(wall_time, bool) or not isinstance(wall_time, (int, float)):
        errors.append(f"{path}.total_wall_time_seconds must be a number")


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

    analysis_payload = payload.get("analysis", {})
    if isinstance(analysis_payload, dict) and analysis_payload:
        analysis_errors = validate_analysis_payload(analysis_payload)
        if analysis_errors:
            joined = "\n".join(f"- {item}" for item in analysis_errors)
            raise RuntimeError(f"results.analysis failed validation:\n{joined}")
    else:
        analysis_payload = generate_analysis_payload(payload)

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
    payload_for_bundle["analysis"] = analysis_payload

    task_pack = str(config["task_pack"])
    task_pack_version, task_pack_source = _resolve_task_pack_version_for_export(config)
    task_pack_hash = str(config.get("task_pack_hash", "")).strip()
    task_pack_license = str(config.get("task_pack_license", "")).strip() or None
    if task_pack_source == "external":
        if not task_pack_hash:
            raise RuntimeError("External task pack results must include config.task_pack_hash.")
        if not SHA256_RE.fullmatch(task_pack_hash):
            raise RuntimeError(f"External task pack hash has invalid format: {task_pack_hash}")

    inferred_command = _infer_cli_command(payload)
    command_used = cli_command.strip() if isinstance(cli_command, str) and cli_command.strip() else inferred_command
    suite = str(config.get("suite", ""))
    protocol_seeds = _extract_protocol_seeds(payload_for_bundle)
    compute_budget_manifest = _normalize_compute_budget_for_manifest(payload_for_bundle)
    payload_for_bundle["compute_budget"] = compute_budget_manifest
    run_group_id = payload_for_bundle.get("run_group_id")

    manifest = {
        "bundle_version": "1",
        "created_at": datetime.now(UTC).isoformat(),
        "tool_version": __version__,
        "results_filename": "results.json",
        "environment_filename": "environment.json",
        "analysis_filename": "analysis.json",
        "task_pack": task_pack,
        "task_pack_version": task_pack_version,
        "task_pack_source": task_pack_source,
        "task_pack_hash": task_pack_hash or None,
        "task_pack_license": task_pack_license,
        "git_commit_hash": commit_hash,
        "cli_command": command_used,
        "official_submission": bool(official_submission),
        "source_results_path": str(results_path),
        "compute_budget": compute_budget_manifest,
    }
    python_env = environment.get("python", {}) if isinstance(environment, dict) else {}
    pip_freeze_sha256 = (
        str(python_env.get("pip_freeze_sha256", "")).strip()
        if isinstance(python_env, dict)
        else ""
    )
    if pip_freeze_sha256 and pip_freeze_sha256 != "unavailable" and not SHA256_RE.fullmatch(
        pip_freeze_sha256
    ):
        pip_freeze_sha256 = "unavailable"
    manifest["pip_freeze_sha256"] = pip_freeze_sha256 or "unavailable"
    if official_submission:
        manifest["protocol_version"] = OFFICIAL_PROTOCOL_VERSION
        manifest["protocol_seeds"] = [int(seed) for seed in protocol_seeds]
        manifest["protocol_seed_count"] = len(protocol_seeds)
        manifest["suite"] = suite
        manifest["run_group_id"] = run_group_id if isinstance(run_group_id, str) else None
        manifest["headline_suite"] = is_headline_suite(suite)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload_for_bundle, indent=2))
        archive.writestr("environment.json", json.dumps(environment, indent=2))
        archive.writestr("analysis.json", json.dumps(analysis_payload, indent=2))
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
            analysis_payload = (
                json.loads(archive.read("analysis.json").decode("utf-8"))
                if "analysis.json" in names
                else None
            )
            manifest_payload = json.loads(archive.read("submission_manifest.json").decode("utf-8"))
    except zipfile.BadZipFile:
        raise RuntimeError(f"Invalid zip archive: {submission_path}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in submission archive: {exc}") from exc

    return {
        "submission_path": str(submission_path),
        "results": results_payload,
        "environment": environment_payload,
        "analysis": analysis_payload,
        "manifest": manifest_payload,
    }


def _validate_official_protocol_requirements(
    *,
    submission_path: Path,
    results_payload: dict[str, Any],
    manifest: dict[str, Any],
    errors: list[str],
    details: dict[str, Any],
) -> None:
    official_submission = bool(manifest.get("official_submission"))
    if not official_submission:
        return

    protocol_version = manifest.get("protocol_version")
    if protocol_version is None:
        details["official_protocol"] = "legacy"
        return

    if not isinstance(protocol_version, str) or not protocol_version.strip():
        errors.append("Manifest protocol_version must be a non-empty string for official submissions.")
        return
    if protocol_version != OFFICIAL_PROTOCOL_VERSION:
        errors.append(
            f"Manifest protocol_version must be `{OFFICIAL_PROTOCOL_VERSION}` for new official bundles "
            f"(got `{protocol_version}`)."
        )

    protocol_seeds_raw = manifest.get("protocol_seeds")
    if not isinstance(protocol_seeds_raw, list) or not protocol_seeds_raw:
        errors.append("Manifest protocol_seeds must be a non-empty list for official protocol bundles.")
        protocol_seeds: list[int] = []
    else:
        protocol_seeds = []
        for index, value in enumerate(protocol_seeds_raw):
            if isinstance(value, bool) or not isinstance(value, int):
                errors.append(f"Manifest protocol_seeds[{index}] must be an integer.")
                continue
            protocol_seeds.append(int(value))

    seed_count = manifest.get("protocol_seed_count")
    if seed_count is not None:
        if isinstance(seed_count, bool) or not isinstance(seed_count, int):
            errors.append("Manifest protocol_seed_count must be an integer when present.")
        elif isinstance(protocol_seeds_raw, list) and seed_count != len(protocol_seeds_raw):
            errors.append(
                "Manifest protocol_seed_count does not match len(protocol_seeds)."
            )

    manifest_budget = manifest.get("compute_budget")
    _validate_compute_budget_manifest(
        budget=manifest_budget,
        path="submission_manifest.compute_budget",
        errors=errors,
    )
    _validate_compute_budget_manifest(
        budget=results_payload.get("compute_budget"),
        path="results.compute_budget",
        errors=errors,
    )

    suite = str(manifest.get("suite", "")).strip()
    if not suite:
        suite = str(results_payload.get("config", {}).get("suite", "")).strip()

    if is_headline_suite(suite):
        expected_seeds = list(OFFICIAL_HEADLINE_SEEDS)
        if protocol_seeds != expected_seeds:
            errors.append(
                f"Headline official bundles must use protocol seeds {expected_seeds} in order."
            )

        replicates = results_payload.get("replicates")
        if not isinstance(replicates, list) or len(replicates) != len(expected_seeds):
            errors.append(
                "Headline official bundles must include multi-seed replicates in results.replicates."
            )
        result_seeds = _extract_protocol_seeds(results_payload)
        if result_seeds != expected_seeds:
            errors.append(
                f"results.replicates seeds must be {expected_seeds} for headline official bundles."
            )

        run_group_id = results_payload.get("run_group_id")
        manifest_group_id = manifest.get("run_group_id")
        if not isinstance(run_group_id, str) or not run_group_id.strip():
            errors.append("results.run_group_id is required for headline official bundles.")
        if not isinstance(manifest_group_id, str) or not manifest_group_id.strip():
            errors.append("Manifest run_group_id is required for headline official bundles.")
        elif isinstance(run_group_id, str) and run_group_id != manifest_group_id:
            errors.append("Manifest run_group_id must match results.run_group_id.")

    details["official_protocol"] = protocol_version
    details["protocol_seeds"] = protocol_seeds
    details["protocol_seed_count"] = len(protocol_seeds)


def verify_submission_bundle(submission_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    details: dict[str, Any] = {"submission_path": str(submission_path)}

    try:
        bundle = read_submission_bundle(submission_path)
    except RuntimeError as exc:
        return {"ok": False, "errors": [str(exc)], "details": details}

    results_payload = bundle["results"]
    environment_payload = bundle["environment"]
    analysis_payload = bundle.get("analysis")
    manifest_payload = bundle["manifest"]

    result_errors = validate_results_payload(results_payload)
    errors.extend(result_errors)

    if results_payload.get("environment") != environment_payload:
        errors.append("environment.json does not match results.environment payload")

    needs_analysis = analysis_required_for_results(results_payload)
    if analysis_payload is None:
        if needs_analysis:
            errors.append(
                "analysis.json is required for multi-replicate results payloads (results.replicates length > 1)"
            )
        else:
            analysis_errors = validate_analysis_payload(generate_analysis_payload(results_payload))
            errors.extend(f"Generated analysis invalid: {item}" for item in analysis_errors)
            if not analysis_errors:
                details["analysis_source"] = "generated_single_replicate"
    else:
        analysis_errors = validate_analysis_payload(analysis_payload)
        errors.extend(f"analysis.json invalid: {item}" for item in analysis_errors)
        if not analysis_errors:
            details["analysis_source"] = "archive"

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
        task_pack_source = str(manifest.get("task_pack_source", "builtin")).strip().lower() or "builtin"
        task_pack_hash = str(manifest.get("task_pack_hash", "")).strip()
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
        analysis_filename = manifest.get("analysis_filename")
        if analysis_filename is not None and analysis_filename != "analysis.json":
            errors.append("Manifest analysis_filename must be `analysis.json` when present")
        pip_freeze_sha256 = manifest.get("pip_freeze_sha256")
        if pip_freeze_sha256 is not None:
            if not isinstance(pip_freeze_sha256, str):
                errors.append("Manifest pip_freeze_sha256 must be a string when present")
            elif pip_freeze_sha256 != "unavailable" and not SHA256_RE.fullmatch(pip_freeze_sha256):
                errors.append("Manifest pip_freeze_sha256 must be a SHA256 digest or `unavailable`")

        if task_pack:
            if task_pack_source == "external":
                if not task_pack_hash:
                    errors.append("External task pack manifests must include task_pack_hash.")
                elif not SHA256_RE.fullmatch(task_pack_hash):
                    errors.append(f"Manifest task_pack_hash has invalid format: {task_pack_hash}")
            else:
                discovered_version = resolve_task_pack_version(task_pack)
                if not discovered_version:
                    errors.append(f"Task pack `{task_pack}` does not exist locally.")
                elif task_pack_version and task_pack_version != discovered_version:
                    errors.append(
                        f"Manifest task_pack_version mismatch: bundle={task_pack_version}, local={discovered_version}"
                    )

        results_config = results_payload.get("config", {})
        if not isinstance(results_config, dict):
            results_config = {}
        results_task_pack = str(results_config.get("task_pack", "")).strip()
        if task_pack and results_task_pack and task_pack != results_task_pack:
            errors.append(
                f"Task pack mismatch between manifest (`{task_pack}`) and results (`{results_task_pack}`)."
            )
        results_pack_source = str(results_config.get("task_pack_source", task_pack_source)).strip().lower()
        if task_pack_source and results_pack_source and task_pack_source != results_pack_source:
            errors.append(
                "Task pack source mismatch between manifest "
                f"(`{task_pack_source}`) and results (`{results_pack_source}`)."
            )
        results_pack_hash = str(results_config.get("task_pack_hash", "")).strip()
        if task_pack_source == "external":
            if results_pack_hash and task_pack_hash and results_pack_hash != task_pack_hash:
                errors.append(
                    "External task pack hash mismatch between manifest "
                    f"(`{task_pack_hash}`) and results (`{results_pack_hash}`)."
                )
            if not results_pack_hash:
                errors.append("results.config.task_pack_hash is required for external task packs.")

        results_commit = str(
            results_payload.get("environment", {}).get("git", {}).get("commit", "")
        ).strip()
        if results_commit and commit_hash and results_commit != commit_hash:
            errors.append(
                f"Commit hash mismatch between manifest (`{commit_hash}`) and results (`{results_commit}`)."
            )

        details["task_pack"] = task_pack
        details["task_pack_version"] = task_pack_version
        details["task_pack_source"] = task_pack_source
        details["task_pack_hash"] = task_pack_hash or None
        details["git_commit_hash"] = commit_hash
        details["cli_command"] = cli_command
        details["pip_freeze_sha256"] = (
            pip_freeze_sha256 if isinstance(pip_freeze_sha256, str) and pip_freeze_sha256 else None
        )
        details["official_submission"] = bool(official_submission)
        details["analysis_required"] = needs_analysis
        _validate_official_protocol_requirements(
            submission_path=submission_path,
            results_payload=results_payload,
            manifest=manifest,
            errors=errors,
            details=details,
        )

    return {"ok": len(errors) == 0, "errors": errors, "details": details}


def render_verification_report(report: dict[str, Any]) -> str:
    if report.get("ok"):
        details = report.get("details", {})
        lines = [
            "Submission verification passed.",
            f"- Submission: {details.get('submission_path')}",
            f"- Task pack: {details.get('task_pack')} ({details.get('task_pack_version')})",
            f"- Pack source: {details.get('task_pack_source', 'builtin')}",
            f"- Commit: {details.get('git_commit_hash')}",
            f"- Label: {'official' if details.get('official_submission') else 'community (not official)'}",
            f"- Command: {details.get('cli_command')}",
            f"- Analysis: {details.get('analysis_source', 'absent')}",
        ]
        if details.get("pip_freeze_sha256"):
            lines.append(f"- Pip freeze hash: {details.get('pip_freeze_sha256')}")
        if details.get("task_pack_hash"):
            lines.append(f"- Pack hash: {details.get('task_pack_hash')}")
        if details.get("official_submission"):
            lines.append(f"- Protocol: {details.get('official_protocol', 'legacy')}")
            if details.get("protocol_seed_count") is not None:
                lines.append(f"- Seeds: {details.get('protocol_seeds', [])}")
        return "\n".join(lines)

    lines = ["Submission verification failed."]
    for error in report.get("errors", []):
        lines.append(f"- {error}")
    return "\n".join(lines)
