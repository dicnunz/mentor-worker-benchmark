from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pvariance

from mentor_worker_benchmark.analysis import DEFAULT_BOOTSTRAP_SAMPLES, generate_analysis_payload
from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.protocol import expand_replicate_seeds, parse_seed_list
from mentor_worker_benchmark.provider_factory import (
    SUPPORTED_PROVIDERS,
    build_client,
    normalize_provider_name,
)
from mentor_worker_benchmark.runner import (
    BenchmarkConfig,
    DEFAULT_MODELS,
    DEFAULT_RUN_MODES,
    compare_results,
    render_compare_report,
    run_benchmark,
    run_multi_seed_benchmark,
    run_sanity_check,
    write_leaderboard,
)
from mentor_worker_benchmark.submission import (
    export_submission_bundle,
    render_verification_report,
    verify_submission_bundle,
)
from mentor_worker_benchmark.tasks.task_pack_v1.curate import CurationConfig, run_curation
from mentor_worker_benchmark.tasks.task_pack_v2.provenance import (
    DEFAULT_MAX_CLUSTERS,
    DEFAULT_SIMILARITY_THRESHOLD,
    write_provenance_artifacts,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _parse_models(raw: str) -> list[str]:
    if raw.strip().lower() == "default":
        return list(DEFAULT_MODELS)
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise ValueError("No models provided. Use comma-separated model names or `default`.")
    return models


def _parse_optional_model_overrides(
    *,
    role: str,
    single_model: str | None,
    plural_models: str | None,
) -> list[str] | None:
    if single_model and plural_models:
        raise ValueError(
            f"Use either --{role}-model or --{role}-models, not both."
        )
    if single_model:
        value = single_model.strip()
        if not value:
            raise ValueError(f"--{role}-model cannot be empty.")
        return [value]
    if plural_models:
        return _parse_models(plural_models)
    return None


def _parse_run_modes(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return tuple(DEFAULT_RUN_MODES)
    if raw.strip().lower() == "default":
        return tuple(DEFAULT_RUN_MODES)

    entries = [token.strip() for token in raw.split(",") if token.strip()]
    if not entries:
        return tuple(DEFAULT_RUN_MODES)
    return tuple(entries)


def _parse_seeds(raw: str | None, *, fallback_seed: int) -> list[int]:
    if raw is None or not raw.strip():
        return [fallback_seed]

    seeds = parse_seed_list(raw)
    if len(set(seeds)) != len(seeds):
        raise ValueError("--seeds must not contain duplicates.")
    return seeds


def _resolve_run_seeds(*, seed: int, seeds_raw: str | None, replicates: int) -> list[int]:
    if replicates < 1:
        raise ValueError("--replicates must be >= 1.")
    has_seed_list = bool(seeds_raw and seeds_raw.strip())
    if has_seed_list:
        if replicates != 1:
            raise ValueError("--replicates cannot be combined with --seeds.")
        return _parse_seeds(seeds_raw, fallback_seed=seed)
    return expand_replicate_seeds(base_seed=seed, replicates=replicates)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _is_git_hash(value: object) -> bool:
    return isinstance(value, str) and _GIT_HASH_RE.fullmatch(value) is not None


def _iter_runs(payload: dict[str, object]) -> list[dict[str, object]]:
    runs = payload.get("runs", [])
    if not isinstance(runs, list):
        return []
    return [run for run in runs if isinstance(run, dict)]


def _safe_pass_value(value: object) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return None


def _task_difficulty_lookup(
    payload: dict[str, object],
    runs: list[dict[str, object]],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    task_ids: set[str] = set()
    for run in runs:
        task_id = run.get("task_id")
        if isinstance(task_id, str) and task_id:
            task_ids.add(task_id)
            difficulty = run.get("task_difficulty")
            if isinstance(difficulty, str) and difficulty:
                lookup[task_id] = difficulty

    unresolved = {task_id for task_id in task_ids if task_id not in lookup}
    if not unresolved:
        return lookup

    environment = payload.get("environment", {})
    if not isinstance(environment, dict):
        return lookup
    task_pack = environment.get("task_pack", {})
    if not isinstance(task_pack, dict):
        return lookup

    manifest_path_value = task_pack.get("manifest_path")
    if not isinstance(manifest_path_value, str) or not manifest_path_value.strip():
        return lookup

    manifest_path = Path(manifest_path_value)
    if not manifest_path.is_absolute():
        manifest_path = (Path.cwd() / manifest_path).resolve()
    if not manifest_path.exists():
        return lookup

    try:
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return lookup
    tasks = metadata.get("tasks", [])
    if not isinstance(tasks, list):
        return lookup

    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        difficulty = task.get("difficulty")
        if not isinstance(task_id, str) or not task_id:
            continue
        if not isinstance(difficulty, str) or not difficulty:
            continue
        if task_id in unresolved:
            lookup[task_id] = difficulty

    return lookup


def _per_task_pass_rates(runs: list[dict[str, object]]) -> list[float]:
    by_task: dict[str, list[float]] = defaultdict(list)
    for run in runs:
        task_id = run.get("task_id")
        pass_value = _safe_pass_value(run.get("pass"))
        if not isinstance(task_id, str) or not task_id:
            continue
        if pass_value is None:
            continue
        by_task[task_id].append(pass_value)
    rates = [mean(values) for _, values in sorted(by_task.items()) if values]
    return rates


def _percent_histogram(values: list[float]) -> dict[str, int]:
    labels = [f"{start:02d}-{start + 9:02d}%" for start in range(0, 100, 10)]
    labels[-1] = "90-100%"
    histogram = {label: 0 for label in labels}
    for value in values:
        pct = min(100.0, max(0.0, float(value) * 100.0))
        bucket_index = min(9, int(pct // 10))
        histogram[labels[bucket_index]] += 1
    return histogram


def _baseline_seed_stats(runs: list[dict[str, object]]) -> tuple[dict[int, float], float]:
    by_seed: dict[int, list[float]] = defaultdict(list)
    for run in runs:
        seed_raw = run.get("seed")
        pass_value = _safe_pass_value(run.get("pass"))
        if isinstance(seed_raw, bool) or not isinstance(seed_raw, (int, float)):
            continue
        if pass_value is None:
            continue
        by_seed[int(seed_raw)].append(pass_value)

    means_by_seed = {
        seed: mean(values)
        for seed, values in sorted(by_seed.items())
        if values
    }
    variance = pvariance(list(means_by_seed.values())) if len(means_by_seed) > 1 else 0.0
    return means_by_seed, variance


def _mentor_lifts(runs: list[dict[str, object]]) -> list[float]:
    baseline_map: dict[tuple[int, str, str], float] = {}
    for run in runs:
        if str(run.get("mode")) != "worker_only":
            continue
        seed_raw = run.get("seed")
        task_id = run.get("task_id")
        worker_model = run.get("worker_model")
        pass_value = _safe_pass_value(run.get("pass"))
        if isinstance(seed_raw, bool) or not isinstance(seed_raw, (int, float)):
            continue
        if not isinstance(task_id, str) or not task_id:
            continue
        if not isinstance(worker_model, str) or not worker_model:
            continue
        if pass_value is None:
            continue
        baseline_map[(int(seed_raw), worker_model, task_id)] = pass_value

    lifts: list[float] = []
    for run in runs:
        if str(run.get("mode")) != "mentor_worker":
            continue
        seed_raw = run.get("seed")
        task_id = run.get("task_id")
        worker_model = run.get("worker_model")
        mentored_pass = _safe_pass_value(run.get("pass"))
        if isinstance(seed_raw, bool) or not isinstance(seed_raw, (int, float)):
            continue
        if not isinstance(task_id, str) or not task_id:
            continue
        if not isinstance(worker_model, str) or not worker_model:
            continue
        if mentored_pass is None:
            continue

        key = (int(seed_raw), worker_model, task_id)
        if key in baseline_map:
            baseline_pass = baseline_map[key]
        else:
            baseline_raw = run.get("baseline_pass")
            baseline_pass = _safe_pass_value(baseline_raw)
            if baseline_pass is None:
                continue
        lifts.append(mentored_pass - baseline_pass)
    return lifts


def _detect_baseline_reuse_groups(runs: list[dict[str, object]]) -> list[str]:
    worker_only_runs = [run for run in runs if str(run.get("mode")) == "worker_only"]
    grouped: dict[tuple[str, int], list[dict[str, object]]] = {}
    for run in worker_only_runs:
        worker_model = str(run.get("worker_model", "unknown"))
        seed_raw = run.get("seed")
        seed = int(seed_raw) if isinstance(seed_raw, (int, float)) and not isinstance(seed_raw, bool) else 0
        grouped.setdefault((worker_model, seed), []).append(run)

    signatures: dict[tuple[tuple[int, ...], tuple[str, ...]], list[tuple[str, int]]] = {}
    for key, items in grouped.items():
        # Small samples can naturally share identical outcome/patch vectors.
        # Require enough task coverage before treating it as suspicious reuse.
        if len(items) < 5:
            continue
        ordered = sorted(items, key=lambda item: str(item.get("task_id", "")))
        baseline_vector = tuple(1 if bool(item.get("pass")) else 0 for item in ordered)
        patch_vector = tuple(str(item.get("patch_hash") or "") for item in ordered)
        signatures.setdefault((baseline_vector, patch_vector), []).append(key)

    suspicious: list[str] = []
    for groups in signatures.values():
        if len(groups) <= 1:
            continue
        suspicious.append(", ".join(f"{worker}@seed{seed}" for worker, seed in sorted(groups)))
    return suspicious


def _audit_patch_hashes(runs: list[dict[str, object]]) -> tuple[bool, str]:
    total_patch_hashes = 0
    missing: list[str] = []
    mismatches: list[str] = []
    short_patch_count = 0

    for run in runs:
        task_id = str(run.get("task_id", "unknown"))
        mode = str(run.get("mode", ""))
        log = run.get("log", {})
        if not isinstance(log, dict):
            log = {}

        if mode == "worker_only":
            extracted = log.get("extracted_patch")
            patch_hash = run.get("patch_hash")
            if isinstance(extracted, str):
                if len(extracted.strip()) < 5:
                    short_patch_count += 1
                if not _is_sha256(patch_hash):
                    missing.append(f"{task_id}:{mode}")
                else:
                    expected = hashlib.sha256(extracted.encode("utf-8")).hexdigest()
                    if patch_hash != expected:
                        mismatches.append(f"{task_id}:{mode}")
                    total_patch_hashes += 1
            continue

        turns = log.get("turns", [])
        if not isinstance(turns, list):
            continue
        for index, turn in enumerate(turns, start=1):
            if not isinstance(turn, dict):
                continue
            extracted = turn.get("extracted_patch")
            patch_hash = turn.get("patch_hash")
            if not isinstance(extracted, str):
                continue
            if len(extracted.strip()) < 5:
                short_patch_count += 1
            if not _is_sha256(patch_hash):
                missing.append(f"{task_id}:{mode}:turn{index}")
            else:
                expected = hashlib.sha256(extracted.encode("utf-8")).hexdigest()
                if patch_hash != expected:
                    mismatches.append(f"{task_id}:{mode}:turn{index}")
                total_patch_hashes += 1

    if short_patch_count > 0:
        return False, f"Found {short_patch_count} patch attempts with length <5 characters."
    if missing:
        return False, "Missing patch hashes for extracted patches: " + ", ".join(missing[:12])
    if mismatches:
        return False, "Patch hash mismatches detected: " + ", ".join(mismatches[:12])
    if total_patch_hashes == 0:
        return False, "No patch hashes recorded in results."
    return True, f"{total_patch_hashes} hashed patch attempts verified."


def _audit_tests_executed(runs: list[dict[str, object]]) -> tuple[bool, str]:
    zero_tasks: list[str] = []
    for run in runs:
        tests_executed = run.get("tests_executed")
        if isinstance(tests_executed, bool) or not isinstance(tests_executed, (int, float)):
            zero_tasks.append(f"{run.get('task_id')}:{run.get('mode')}")
            continue
        if int(tests_executed) <= 0:
            zero_tasks.append(f"{run.get('task_id')}:{run.get('mode')}")

    if zero_tasks:
        return False, "Found runs with tests_executed <= 0: " + ", ".join(zero_tasks[:12])
    return True, f"{len(runs)} runs recorded tests_executed > 0."


def _audit_runtime_distribution(runs: list[dict[str, object]]) -> tuple[bool, str]:
    runtimes: list[float] = []
    for run in runs:
        value = run.get("test_runtime_seconds")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        runtimes.append(float(value))

    if not runtimes:
        return False, "No test runtime evidence found."

    low_count = sum(1 for runtime in runtimes if runtime < 0.1)
    share = low_count / len(runtimes)
    if share > 0.8:
        return False, (
            "tests may not be executing "
            f"(runtime <0.1s for {low_count}/{len(runtimes)} runs)."
        )
    return True, f"Runtime distribution plausible ({low_count}/{len(runtimes)} under 0.1s)."


def _audit_baseline_reuse(runs: list[dict[str, object]]) -> tuple[bool, str]:
    suspicious = _detect_baseline_reuse_groups(runs)
    if suspicious:
        return False, (
            "Potential artifact reuse detected across worker-only baseline vectors: "
            + "; ".join(suspicious[:4])
        )
    return True, "Baseline vectors appear freshly computed per run."


def _audit_commit_metadata(payload: dict[str, object]) -> tuple[bool, str]:
    env = payload.get("environment", {})
    if not isinstance(env, dict):
        return False, "Missing results.environment metadata."
    git_data = env.get("git", {})
    if not isinstance(git_data, dict):
        return False, "Missing results.environment.git metadata."

    artifact_commit = git_data.get("commit_hash") or git_data.get("commit")
    if not _is_git_hash(artifact_commit):
        return False, "Invalid or missing artifact commit hash."

    artifact_commit_text = str(artifact_commit)
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{artifact_commit_text}^{{commit}}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError:
        return False, f"Artifact commit not found in local git object store: {artifact_commit_text}"

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        return False, f"Unable to resolve local HEAD commit: {exc}"

    if artifact_commit_text != head:
        return False, (
            "Artifact commit metadata mismatch: "
            f"results={artifact_commit_text}, local_head={head}"
        )
    return True, f"Artifact commit verified: {artifact_commit_text}"


def _head_lines(text: str, *, max_lines: int = 50) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"


def _print_debug_report(results: dict[str, object]) -> None:
    runs = results.get("runs", [])
    if not isinstance(runs, list):
        return

    print("\n[DEBUG] Detailed run trace")
    for index, run in enumerate(runs, start=1):
        if not isinstance(run, dict):
            continue
        mode = str(run.get("mode", ""))
        task_id = str(run.get("task_id", ""))
        worker_model = str(run.get("worker_model", ""))
        mentor_model = run.get("mentor_model")
        final_pass = bool(run.get("pass", False))
        print(
            f"\n[DEBUG][Run {index}] mode={mode} task={task_id} "
            f"worker={worker_model} mentor={mentor_model} final_pass={final_pass}"
        )

        log = run.get("log", {})
        if not isinstance(log, dict):
            continue

        if mode == "worker_only":
            accepted = bool(log.get("extracted_patch"))
            reason = str(log.get("patch_log", "no patch log"))
            print(f"[DEBUG] attempt=1 patch={'accepted' if accepted else 'rejected'}")
            if accepted:
                print("[DEBUG] patch_reason=valid unified diff extracted")
            else:
                print(f"[DEBUG] reject_reason={reason}")
            patch_applied = bool(log.get("patch_applied", False))
            print(f"[DEBUG] attempt=1 patch_applied={patch_applied}")
            print("[DEBUG] attempt=1 patch_log_first_20_lines:")
            print(_head_lines(reason, max_lines=20) or "(empty)")
            initial_output = _head_lines(str(log.get("initial_test_output", "")))
            final_output = _head_lines(str(log.get("final_test_output", "")))
            print("[DEBUG] attempt=1 pytest_initial_first_50_lines:")
            print(initial_output or "(empty)")
            print("[DEBUG] attempt=1 pytest_after_patch_first_50_lines:")
            print(final_output or "(empty)")
            continue

        turns = log.get("turns", [])
        if not isinstance(turns, list):
            continue
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            turn_id = int(turn.get("turn", 0))
            accepted = bool(turn.get("extracted_patch"))
            reason = str(turn.get("patch_log", "no patch log"))
            print(f"[DEBUG] attempt={turn_id} patch={'accepted' if accepted else 'rejected'}")
            if accepted:
                print("[DEBUG] patch_reason=valid unified diff extracted")
            else:
                print(f"[DEBUG] reject_reason={reason}")
            patch_applied = bool(turn.get("patch_applied", False))
            print(f"[DEBUG] attempt={turn_id} patch_applied={patch_applied}")
            print(f"[DEBUG] attempt={turn_id} patch_log_first_20_lines:")
            print(_head_lines(reason, max_lines=20) or "(empty)")
            pytest_output = _head_lines(str(turn.get("test_output", "")))
            print(f"[DEBUG] attempt={turn_id} pytest_first_50_lines:")
            print(pytest_output or "(empty)")


def cmd_setup(args: argparse.Namespace) -> int:
    models = _parse_models(args.models)
    client = OllamaClient()

    status = client.ensure_server_running(auto_start=True)
    print(status.message)
    if not status.reachable:
        return 1

    if args.skip_pull:
        print("Skipping model pulls (--skip-pull).")
        return 0

    print(f"Ensuring {len(models)} model(s) are available locally...")
    try:
        pulled = client.ensure_models(models)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if pulled:
        print("Pulled models:")
        for model in pulled:
            print(f"- {model}")
    else:
        print("All requested models are already present.")
    return 0


def _normalize_probe_response(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _probe_model_stability(
    *,
    client: Any,
    model: str,
    attempts: int,
    seed: int,
    num_predict: int,
) -> dict[str, Any]:
    expected_response = "STABLE_OK"
    responses: list[str] = []
    latencies: list[float] = []
    errors: list[str] = []

    for _ in range(attempts):
        started = time.perf_counter()
        try:
            response = client.chat(
                model=model,
                messages=[{"role": "user", "content": "Reply with exactly STABLE_OK and nothing else."}],
                temperature=0.0,
                top_p=1.0,
                num_predict=num_predict,
                seed=seed,
            )
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        latencies.append(time.perf_counter() - started)
        responses.append(_normalize_probe_response(response))

    unique_responses = sorted(set(responses))
    stable = (
        not errors
        and len(unique_responses) == 1
        and len(responses) == attempts
        and unique_responses == [expected_response]
    )
    return {
        "model": model,
        "attempts": attempts,
        "seed": int(seed),
        "success_count": len(responses),
        "error_count": len(errors),
        "stable": stable,
        "expected_response": expected_response,
        "responses": unique_responses,
        "errors": errors,
        "latency_seconds": [round(item, 4) for item in latencies],
        "avg_latency_seconds": round(mean(latencies), 4) if latencies else None,
    }


def cmd_preflight(args: argparse.Namespace) -> int:
    try:
        models = _parse_models(args.models)
        provider = normalize_provider_name(args.provider)
    except ValueError as exc:
        print(str(exc))
        return 1

    if args.attempts < 1:
        print("--attempts must be >= 1")
        return 1

    try:
        client = build_client(
            provider=provider,
            timeout_seconds=args.model_timeout,
            reasoning_level="none",
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if isinstance(client, OllamaClient):
        status = client.ensure_server_running(auto_start=False)
        if not status.reachable:
            print(status.message)
            return 1
        local_models = client.list_local_models()
        missing = [model for model in models if model not in local_models]
        if missing:
            print("Missing models in Ollama: " + ", ".join(missing))
            return 1

    report = {
        "provider": provider,
        "model_timeout_seconds": int(args.model_timeout),
        "attempts": int(args.attempts),
        "seed": int(args.seed),
        "num_predict": int(args.num_predict),
        "models": [
            _probe_model_stability(
                client=client,
                model=model,
                attempts=args.attempts,
                seed=args.seed,
                num_predict=args.num_predict,
            )
            for model in models
        ],
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    all_stable = True
    for item in report["models"]:
        status = "stable" if item["stable"] else "UNSTABLE"
        print(
            f"{item['model']}: {status} "
            f"(successes={item['success_count']}/{item['attempts']}, "
            f"errors={item['error_count']}, avg_latency={item['avg_latency_seconds']})"
        )
        if item["responses"]:
            print("  responses: " + ", ".join(item["responses"]))
        if item["errors"]:
            print("  last_error: " + item["errors"][-1])
        all_stable = all_stable and bool(item["stable"])

    if all_stable:
        print("Backend preflight passed. Stability is sufficient for local verification.")
        return 0

    print(
        "Backend preflight failed. Local backend stability is insufficient for strict local "
        "verification; do not claim strict reproducibility from this run."
    )
    return 1


def cmd_run(args: argparse.Namespace) -> int:
    try:
        models = _parse_models(args.models)
        mentor_models_override = _parse_optional_model_overrides(
            role="mentor",
            single_model=args.mentor_model,
            plural_models=args.mentor_models,
        )
        worker_models_override = _parse_optional_model_overrides(
            role="worker",
            single_model=args.worker_model,
            plural_models=args.worker_models,
        )
    except ValueError as exc:
        print(str(exc))
        return 1

    mentor_models = list(mentor_models_override or models)
    worker_models = list(worker_models_override or models)

    try:
        provider = normalize_provider_name(args.provider)
        mentor_provider = normalize_provider_name(args.mentor_provider or provider)
        worker_provider = normalize_provider_name(args.worker_provider or provider)
    except ValueError as exc:
        print(str(exc))
        return 1

    run_modes = _parse_run_modes(args.run_modes)
    try:
        seeds = _resolve_run_seeds(
            seed=args.seed,
            seeds_raw=args.seeds,
            replicates=args.replicates,
        )
    except ValueError as exc:
        print(str(exc))
        return 1

    if args.max_turns < 1:
        print("--max-turns must be >= 1")
        return 1
    if args.test_timeout < 1:
        print("--test-timeout must be >= 1")
        return 1
    if args.model_retries < 0:
        print("--model-retries must be >= 0")
        return 1
    if args.model_retry_backoff < 0:
        print("--model-retry-backoff must be >= 0")
        return 1
    if args.tasks and args.suite:
        print("--tasks provided; ignoring --suite for task selection.")

    model_timeout_seconds = args.model_timeout
    if args.timeout is not None:
        print("`--timeout` is deprecated; use `--model-timeout`.", file=sys.stderr)
        model_timeout_seconds = args.timeout

    try:
        if mentor_provider == worker_provider:
            shared_client = build_client(
                provider=mentor_provider,
                timeout_seconds=model_timeout_seconds,
                reasoning_level=args.reasoning_level,
            )
            mentor_client = shared_client
            worker_client = shared_client
        else:
            mentor_client = build_client(
                provider=mentor_provider,
                timeout_seconds=model_timeout_seconds,
                reasoning_level=args.reasoning_level,
            )
            worker_client = build_client(
                provider=worker_provider,
                timeout_seconds=model_timeout_seconds,
                reasoning_level=args.reasoning_level,
            )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if isinstance(mentor_client, OllamaClient):
        status = mentor_client.ensure_server_running(auto_start=False)
        if not status.reachable:
            print(status.message)
            print("Run `python -m mentor_worker_benchmark setup` first.")
            return 1
    if isinstance(worker_client, OllamaClient) and worker_client is not mentor_client:
        status = worker_client.ensure_server_running(auto_start=False)
        if not status.reachable:
            print(status.message)
            print("Run `python -m mentor_worker_benchmark setup` first.")
            return 1

    if not args.skip_model_check:
        if isinstance(mentor_client, OllamaClient):
            local_models = mentor_client.list_local_models()
            missing = [model for model in sorted(set(mentor_models)) if model not in local_models]
            if missing:
                print("Missing mentor models in Ollama: " + ", ".join(missing))
                print("Run `python -m mentor_worker_benchmark setup` to pull them.")
                return 1
        if isinstance(worker_client, OllamaClient):
            local_models = worker_client.list_local_models()
            missing = [model for model in sorted(set(worker_models)) if model not in local_models]
            if missing:
                print("Missing worker models in Ollama: " + ", ".join(missing))
                print("Run `python -m mentor_worker_benchmark setup` to pull them.")
                return 1

    config = BenchmarkConfig(
        models=models,
        mentor_models_override=mentor_models,
        worker_models_override=worker_models_override,
        provider=provider,
        mentor_provider=mentor_provider,
        worker_provider=worker_provider,
        max_turns=args.max_turns,
        task_pack=args.task_pack,
        task_pack_path=Path(args.task_pack_path).resolve() if args.task_pack_path else None,
        suite=args.suite,
        task_selector=args.tasks,
        seed=seeds[0],
        results_path=Path(args.results_path),
        run_modes=run_modes,
        repro_mode=args.repro,
        stronger_worker_model=args.stronger_worker_model,
        worker_num_predict_override=args.worker_num_predict,
        mentor_num_predict_override=args.mentor_num_predict,
        timeout_seconds=model_timeout_seconds,
        test_timeout_seconds=args.test_timeout,
        model_retry_attempts=args.model_retries,
        model_retry_backoff_seconds=args.model_retry_backoff,
    )

    try:
        if len(seeds) > 1:
            results = run_multi_seed_benchmark(
                config,
                seeds=seeds,
                mentor_client=mentor_client,
                worker_client=worker_client,
            )
        else:
            results = run_benchmark(config, mentor_client=mentor_client, worker_client=worker_client)
    except KeyboardInterrupt:
        checkpoint_path = config.results_path.with_name(f"{config.results_path.stem}.checkpoint.jsonl")
        print(
            "Benchmark interrupted. Completed units remain in the checkpoint log and can be resumed "
            f"by rerunning the same command with the same --results-path.\nCheckpoint JSONL: {checkpoint_path}"
        )
        return 130
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1

    print(f"Completed {results['summary']['total_runs']} runs.")
    if len(seeds) > 1:
        print(
            f"Replicates: {len(seeds)} "
            f"(seeds={','.join(str(seed) for seed in seeds)}, run_group_id={results.get('run_group_id')})"
        )
    print("Runs by mode:")
    for mode, count in sorted(results["summary"]["runs_by_mode"].items()):
        print(f"- {mode}: {count}")
    print(f"Results JSON: {config.results_path}")
    print(f"Leaderboard: {config.results_path.parent / 'leaderboard.md'}")
    checkpoint_path = config.results_path.with_name(f"{config.results_path.stem}.checkpoint.jsonl")
    print(f"Checkpoint JSONL: {checkpoint_path}")
    if args.debug:
        _print_debug_report(results)
    return 0


def cmd_sanity(args: argparse.Namespace) -> int:
    if args.tasks and args.suite:
        print("--tasks provided; ignoring --suite for task selection.")
    try:
        summary = run_sanity_check(
            task_pack=args.task_pack,
            task_pack_path=Path(args.task_pack_path).resolve() if args.task_pack_path else None,
            suite=args.suite,
            task_selector=args.tasks,
            seed=args.seed,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(
        f"Sanity checked {summary['task_count']} tasks from `{summary['task_pack']}` "
        f"(suite={summary['suite']})."
    )
    print(
        f"Expected failures: {summary['expected_failures']}, "
        f"unexpected passes: {summary['unexpected_passes']}, "
        f"broken harness tasks: {summary['broken_tasks']}"
    )
    print(f"Wall time: {summary['wall_time_seconds']}s")
    return 0 if summary["unexpected_passes"] == 0 and summary["broken_tasks"] == 0 else 1


def cmd_leaderboard(args: argparse.Namespace) -> int:
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return 1

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    output = Path(args.output)
    write_leaderboard(payload, output)
    print(f"Leaderboard written to: {output}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    before_path = Path(args.before)
    after_path = Path(args.after)
    if not before_path.exists():
        print(f"Before results file not found: {before_path}")
        return 1
    if not after_path.exists():
        print(f"After results file not found: {after_path}")
        return 1

    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))

    comparison = compare_results(before, after)
    report = render_compare_report(comparison)
    print(report)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return 1

    try:
        payload = json.loads(results_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON at {results_path}: {exc}")
        return 1

    try:
        analysis = generate_analysis_payload(
            payload,
            bootstrap_samples=args.bootstrap_samples,
            bootstrap_seed=args.bootstrap_seed,
        )
    except ValueError as exc:
        print(str(exc))
        return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")

    print(f"Analysis written to: {out_path}")
    print(f"Groups: {analysis.get('group_count', 0)}")
    print(
        f"Bootstrap: samples={analysis.get('bootstrap_samples')} seed={analysis.get('bootstrap_seed')}"
    )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return 1

    try:
        payload = json.loads(results_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON at {results_path}: {exc}")
        return 1

    if not isinstance(payload, dict):
        print("Results payload must be a JSON object.")
        return 1

    runs = _iter_runs(payload)
    if not runs:
        print("Results payload contains no runs to audit.")
        return 1

    checks = [
        ("real patches generated", _audit_patch_hashes(runs)),
        ("tests executed", _audit_tests_executed(runs)),
        ("baseline computed", _audit_baseline_reuse(runs)),
        ("runtime distribution plausible", _audit_runtime_distribution(runs)),
        ("artifact integrity verified", _audit_commit_metadata(payload)),
    ]

    all_ok = True
    for label, (ok, detail) in checks:
        prefix = "✓" if ok else "✗"
        print(f"{prefix} {label}")
        print(f"  {detail}")
        if not ok:
            all_ok = False

    return 0 if all_ok else 1


def cmd_healthcheck(args: argparse.Namespace) -> int:
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return 1

    try:
        payload = json.loads(results_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON at {results_path}: {exc}")
        return 1

    if not isinstance(payload, dict):
        print("Results payload must be a JSON object.")
        return 1

    runs = _iter_runs(payload)
    if not runs:
        print("Results payload contains no runs.")
        return 1

    baseline_runs = [run for run in runs if str(run.get("mode")) == "worker_only"]
    analyzed_runs = baseline_runs if baseline_runs else runs
    analyzed_label = "baseline worker_only" if baseline_runs else "all modes (fallback)"

    difficulty_lookup = _task_difficulty_lookup(payload, runs)
    task_ids = sorted(
        {
            str(run.get("task_id"))
            for run in runs
            if isinstance(run.get("task_id"), str) and str(run.get("task_id"))
        }
    )
    difficulty_counts: Counter[str] = Counter(
        difficulty_lookup.get(task_id, "unknown") for task_id in task_ids
    )

    pass_rates = _per_task_pass_rates(analyzed_runs)
    pass_histogram = _percent_histogram(pass_rates)
    solved_rate = mean(pass_rates) if pass_rates else 0.0

    seed_means, seed_variance = _baseline_seed_stats(baseline_runs)

    lifts = _mentor_lifts(runs)
    lift_mean = mean(lifts) if lifts else 0.0
    lift_variance = pvariance(lifts) if len(lifts) > 1 else 0.0
    lift_sign_counts = {
        "negative": sum(1 for value in lifts if value < 0.0),
        "zero": sum(1 for value in lifts if value == 0.0),
        "positive": sum(1 for value in lifts if value > 0.0),
    }

    print("Benchmark Healthcheck")
    print(f"Results: {results_path}")
    print(f"Runs analyzed: {len(runs)}")
    print(f"Pass-rate basis: {analyzed_label}")

    print("\nTask difficulty distribution:")
    for difficulty, count in sorted(difficulty_counts.items()):
        print(f"- {difficulty}: {count}")

    print("\nPass-rate histogram (per-task):")
    for bucket, count in pass_histogram.items():
        print(f"- {bucket}: {count}")
    print(f"- solved_rate_mean: {solved_rate:.4f}")

    print("\nBaseline variance across seeds:")
    if seed_means:
        for seed, rate in seed_means.items():
            print(f"- seed {seed}: {rate:.4f}")
        print(f"- variance: {seed_variance:.8f}")
    else:
        print("- no baseline worker_only runs found")

    print("\nMentor lift distribution:")
    print(f"- sample_count: {len(lifts)}")
    print(f"- mean: {lift_mean:.4f}")
    print(f"- variance: {lift_variance:.8f}")
    print(f"- negative: {lift_sign_counts['negative']}")
    print(f"- zero: {lift_sign_counts['zero']}")
    print(f"- positive: {lift_sign_counts['positive']}")

    warnings: list[str] = []
    if solved_rate > 0.80:
        warnings.append(
            f"Benchmark may be too easy: solved_rate_mean={solved_rate:.2%} (>80%)."
        )
    if solved_rate < 0.05:
        warnings.append(
            f"Benchmark may be too hard: solved_rate_mean={solved_rate:.2%} (<5%)."
        )

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- WARNING: {warning}")
    else:
        print("\nWarnings:\n- none")

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        manifest = export_submission_bundle(
            results_path=Path(args.results),
            out_path=Path(args.out),
            cli_command=args.command,
            official_submission=args.official,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Submission bundle written: {args.out}")
    print(f"Task pack: {manifest['task_pack']} ({manifest['task_pack_version']})")
    print(f"Commit: {manifest['git_commit_hash']}")
    if manifest.get("official_submission"):
        print(
            "Official protocol: "
            f"{manifest.get('protocol_version', 'legacy')} "
            f"seeds={manifest.get('protocol_seeds', [])}"
        )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    report = verify_submission_bundle(Path(args.submission))
    print(render_verification_report(report))
    return 0 if report.get("ok") else 1


def cmd_curate(args: argparse.Namespace) -> int:
    config = CurationConfig(
        task_pack=args.task_pack,
        seed=args.seed,
        similarity_threshold=args.similarity_threshold,
        triviality_sample_size=args.triviality_sample_size,
        full_triviality_model_check=args.full_triviality_model_check,
        max_replacement_attempts=args.max_replacement_attempts,
        results_dir=Path(args.results_dir),
        worker_num_predict=args.worker_num_predict,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
    )

    try:
        payload = run_curation(config)
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1

    print(
        f"Curation finished: replaced {payload['replacements']['count']} tasks. "
        f"Duplicate clusters {payload['duplicates']['cluster_count_before']} -> "
        f"{payload['duplicates']['cluster_count_after']}."
    )
    print(f"Report JSON: {config.results_dir / 'curation_report.json'}")
    print(f"Report Markdown: {config.results_dir / 'curation_report.md'}")
    return 0


def cmd_provenance(args: argparse.Namespace) -> int:
    if args.task_pack != "task_pack_v2":
        print("`provenance` currently supports only --task-pack task_pack_v2.")
        return 1

    try:
        payload = write_provenance_artifacts(
            seed=args.seed,
            similarity_threshold=args.similarity_threshold,
            max_clusters=args.max_clusters,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    similarity = payload["checks"]["similarity_scan"]
    originality = payload["checks"]["originality_scan"]
    print(
        f"Provenance updated for {payload['pack_name']} "
        f"(clusters={similarity['cluster_count']}, flagged_files={originality['flagged_files_count']})."
    )
    print("Artifacts:")
    print("- mentor_worker_benchmark/tasks/task_pack_v2/provenance.json")
    print("- mentor_worker_benchmark/tasks/task_pack_v2/PROVENANCE.md")

    if args.fail_on_overlap and int(similarity["cluster_count"]) > 0:
        print("Overlap clusters detected and --fail-on-overlap set.")
        return 1
    if int(originality["flagged_files_count"]) > 0:
        print("Originality marker scan found potential external references.")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mentor-worker-benchmark",
        description="Benchmark local mentor/worker LLM collaboration over objective coding tasks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Verify Ollama and pull required models.")
    setup.add_argument("--models", default="default", help="Comma-separated model list or `default`.")
    setup.add_argument("--skip-pull", action="store_true", help="Skip `ollama pull` checks.")
    setup.set_defaults(func=cmd_setup)

    preflight = subparsers.add_parser(
        "preflight",
        help="Probe backend stability for lightweight local verification.",
    )
    preflight.add_argument("--models", default="phi3:mini,llama3.1:8b")
    preflight.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default="ollama",
        help="Provider to probe (default: ollama).",
    )
    preflight.add_argument("--model-timeout", type=int, default=30)
    preflight.add_argument("--attempts", type=int, default=2)
    preflight.add_argument("--seed", type=int, default=1337)
    preflight.add_argument("--num-predict", type=int, default=24)
    preflight.add_argument("--out", default=None, help="Optional JSON path for the preflight report.")
    preflight.set_defaults(func=cmd_preflight)

    run = subparsers.add_parser("run", help="Run benchmark suites and ablations.")
    run.add_argument("--models", default="default", help="Comma-separated model list or `default`.")
    run.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        default="ollama",
        help="LLM provider for both roles (default: ollama).",
    )
    run.add_argument(
        "--mentor-provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help="Optional provider override for mentor role.",
    )
    run.add_argument(
        "--worker-provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help="Optional provider override for worker role.",
    )
    run.add_argument(
        "--mentor-models",
        default=None,
        help="Optional comma-separated mentor model list. Defaults to --models.",
    )
    run.add_argument(
        "--mentor-model",
        default=None,
        help="Optional single mentor model name (use instead of --mentor-models).",
    )
    run.add_argument(
        "--worker-models",
        default=None,
        help="Optional comma-separated worker model list. Defaults to --models.",
    )
    run.add_argument(
        "--worker-model",
        default=None,
        help="Optional single worker model name (use instead of --worker-models).",
    )
    run.add_argument(
        "--reasoning-level",
        choices=["none", "low", "medium", "high"],
        default="none",
        help=(
            "Reasoning effort hint for providers/models that support it "
            "(currently applies to openai)."
        ),
    )
    run.add_argument("--max-turns", type=int, default=4)
    run.add_argument("--task-pack", default="task_pack_v2")
    run.add_argument(
        "--task-pack-path",
        default=None,
        help="Optional path to an external task pack directory (metadata.json + tasks).",
    )
    run.add_argument("--suite", choices=["quick", "dev10", "dev50", "dev", "test", "all"], default=None)
    run.add_argument(
        "--tasks",
        default=None,
        help="Legacy explicit selector: all, quick, or comma-separated task ids. Overrides --suite.",
    )
    run.add_argument("--seed", type=int, default=1337)
    run.add_argument(
        "--seeds",
        default=None,
        help=(
            "Optional comma-separated seed list for multi-replicate runs. "
            "When set, --seed is ignored."
        ),
    )
    run.add_argument(
        "--replicates",
        type=int,
        default=1,
        help=(
            "Number of deterministic replicate seeds to run (derived from --seed). "
            "Cannot be combined with --seeds."
        ),
    )
    run.add_argument("--repro", action="store_true", help="Enable deterministic reproducibility mode.")
    run.add_argument(
        "--run-modes",
        default="default",
        help=(
            "Comma-separated run modes. "
            "Allowed: worker_only,mentor_worker,mentor_only_suggestion_noise,stronger_worker,mentor_swap"
        ),
    )
    run.add_argument(
        "--stronger-worker-model",
        default=None,
        help="Optional explicit stronger worker model to use when run mode includes stronger_worker.",
    )
    run.add_argument(
        "--results-path",
        default="results/results.json",
        help=(
            "Final results JSON path. Resume state is stored alongside it as "
            "<stem>.checkpoint.jsonl; multi-seed runs also emit <stem>.seed-<seed>.json."
        ),
    )
    run.add_argument(
        "--model-timeout",
        type=int,
        default=180,
        help="Per-model-call timeout in seconds.",
    )
    run.add_argument(
        "--test-timeout",
        type=int,
        default=8,
        help="Per-pytest execution timeout in seconds.",
    )
    run.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Deprecated alias for --model-timeout.",
    )
    run.add_argument(
        "--model-retries",
        type=int,
        default=1,
        help="Bounded retry count for transient backend timeouts/errors.",
    )
    run.add_argument(
        "--model-retry-backoff",
        type=float,
        default=1.0,
        help="Base backoff in seconds between transient model-call retries.",
    )
    run.add_argument(
        "--debug",
        action="store_true",
        help="Print per-attempt patch/test diagnostics for each run.",
    )
    run.add_argument(
        "--worker-num-predict",
        type=int,
        default=None,
        help="Optional max completion tokens for worker generations.",
    )
    run.add_argument(
        "--mentor-num-predict",
        type=int,
        default=None,
        help="Optional max completion tokens for mentor generations.",
    )
    run.add_argument(
        "--skip-model-check",
        action="store_true",
        help="Skip local model presence check (advanced).",
    )
    run.set_defaults(func=cmd_run)

    sanity = subparsers.add_parser(
        "sanity",
        help="Run pytest sanity checks on task starters (no model interaction).",
    )
    sanity.add_argument("--task-pack", default="task_pack_v2")
    sanity.add_argument(
        "--task-pack-path",
        default=None,
        help="Optional path to an external task pack directory (metadata.json + tasks).",
    )
    sanity.add_argument("--suite", choices=["quick", "dev10", "dev50", "dev", "test", "all"], default="all")
    sanity.add_argument(
        "--tasks",
        default=None,
        help="Legacy explicit selector: all, quick, or comma-separated task ids. Overrides --suite.",
    )
    sanity.add_argument("--seed", type=int, default=1337)
    sanity.set_defaults(func=cmd_sanity)

    leaderboard = subparsers.add_parser("leaderboard", help="Render leaderboard markdown from JSON results.")
    leaderboard.add_argument("--results", default="results/results.json")
    leaderboard.add_argument("--output", default="results/leaderboard.md")
    leaderboard.set_defaults(func=cmd_leaderboard)

    compare = subparsers.add_parser("compare", help="Compare two results JSON files and report deltas.")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.set_defaults(func=cmd_compare)

    analyze = subparsers.add_parser(
        "analyze",
        help="Compute deterministic multi-replicate pass-rate CIs and lift significance from results JSON.",
    )
    analyze.add_argument("--results", required=True, help="Path to benchmark results JSON.")
    analyze.add_argument("--out", required=True, help="Path to write analysis JSON.")
    analyze.add_argument(
        "--bootstrap-samples",
        type=int,
        default=DEFAULT_BOOTSTRAP_SAMPLES,
        help=f"Number of bootstrap samples per group (default: {DEFAULT_BOOTSTRAP_SAMPLES}).",
    )
    analyze.add_argument(
        "--bootstrap-seed",
        type=int,
        default=None,
        help="Optional base bootstrap seed override (deterministic if omitted).",
    )
    analyze.set_defaults(func=cmd_analyze)

    audit = subparsers.add_parser(
        "audit",
        help="Verify harness integrity signals in a benchmark results JSON artifact.",
    )
    audit.add_argument("results", help="Path to benchmark results JSON.")
    audit.set_defaults(func=cmd_audit)

    healthcheck = subparsers.add_parser(
        "healthcheck",
        help="Compute benchmark health diagnostics from a results JSON artifact.",
    )
    healthcheck.add_argument("--results", default="results/results.json")
    healthcheck.set_defaults(func=cmd_healthcheck)

    export = subparsers.add_parser("export", help="Export a standardized submission zip from results.json.")
    export.add_argument("--results", default="results/results.json")
    export.add_argument("--out", required=True)
    export.add_argument("--command", default=None, help="Optional explicit CLI command used for the run.")
    export.add_argument(
        "--official",
        action="store_true",
        help="Mark bundle as official (maintainer-approved standardized run).",
    )
    export.set_defaults(func=cmd_export)

    verify = subparsers.add_parser("verify", help="Verify a standardized submission zip.")
    verify.add_argument("--submission", required=True)
    verify.set_defaults(func=cmd_verify)

    curate = subparsers.add_parser(
        "curate",
        help="Run task-pack quality gates, regenerate flagged tasks, and emit curation reports.",
    )
    curate.add_argument("--task-pack", default="task_pack_v1")
    curate.add_argument("--seed", type=int, default=1337)
    curate.add_argument("--similarity-threshold", type=float, default=0.92)
    curate.add_argument("--triviality-sample-size", type=int, default=72)
    curate.add_argument("--full-triviality-model-check", action="store_true")
    curate.add_argument("--max-replacement-attempts", type=int, default=10)
    curate.add_argument("--worker-num-predict", type=int, default=220)
    curate.add_argument("--ollama-timeout-seconds", type=int, default=60)
    curate.add_argument("--results-dir", default="results")
    curate.set_defaults(func=cmd_curate)

    provenance = subparsers.add_parser(
        "provenance",
        help="Generate task_pack_v2 provenance manifest and overlap/originality checks.",
    )
    provenance.add_argument("--task-pack", default="task_pack_v2")
    provenance.add_argument("--seed", type=int, default=None)
    provenance.add_argument("--similarity-threshold", type=float, default=DEFAULT_SIMILARITY_THRESHOLD)
    provenance.add_argument("--max-clusters", type=int, default=DEFAULT_MAX_CLUSTERS)
    provenance.add_argument("--fail-on-overlap", action="store_true")
    provenance.set_defaults(func=cmd_provenance)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = args.func(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])
