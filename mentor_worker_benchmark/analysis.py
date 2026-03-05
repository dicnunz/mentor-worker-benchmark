from __future__ import annotations

import hashlib
import json
import random
from math import ceil, floor
from statistics import mean
from typing import Any

ANALYSIS_VERSION = "0.4.0"
CI_METHOD = "bootstrap_percentile_95_task_family_within_replicate_pooled"
PAIRED_SIGNIFICANCE_METHOD = "paired_bootstrap_over_task_families"
DEFAULT_BOOTSTRAP_SAMPLES = 2000


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _safe_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _round_or_none(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _normalize_run_modes(config: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
    run_modes = config.get("run_modes", [])
    modes: list[str] = []
    if isinstance(run_modes, list):
        for item in run_modes:
            if isinstance(item, str) and item and item not in modes:
                modes.append(item)
    for run in runs:
        mode = run.get("mode")
        if isinstance(mode, str) and mode and mode not in modes:
            modes.append(mode)
    return modes


def _materialize_legacy_replicate(payload: dict[str, Any]) -> dict[str, Any]:
    config = payload.get("config", {}) if isinstance(payload.get("config"), dict) else {}
    runs = payload.get("runs", []) if isinstance(payload.get("runs"), list) else []
    generation = config.get("generation", {}) if isinstance(config.get("generation"), dict) else {}
    seed = _safe_int(generation.get("seed"))
    if seed is None:
        seed = _safe_int(config.get("seed"))
    if seed is None:
        seed = 0
    return {
        "replicate_id": str(payload.get("replicate_id", "replicate_1")),
        "seed": seed,
        "generated_at": str(payload.get("generated_at", "")),
        "config": config,
        "runs": runs,
    }


def extract_replicates(results_payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_replicates = results_payload.get("replicates")
    if not isinstance(raw_replicates, list) or not raw_replicates:
        return [_materialize_legacy_replicate(results_payload)]

    top_config = results_payload.get("config", {}) if isinstance(results_payload.get("config"), dict) else {}
    extracted: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_replicates, start=1):
        if not isinstance(raw, dict):
            continue
        config = raw.get("config", {})
        if not isinstance(config, dict):
            config = top_config
        runs = raw.get("runs", [])
        if not isinstance(runs, list):
            runs = []
        generation = config.get("generation", {}) if isinstance(config.get("generation"), dict) else {}
        seed = _safe_int(raw.get("seed"))
        if seed is None:
            seed = _safe_int(generation.get("seed"))
        if seed is None:
            seed = _safe_int(config.get("seed"))
        if seed is None:
            seed = index - 1

        replicate_id = raw.get("replicate_id")
        if not isinstance(replicate_id, str) or not replicate_id.strip():
            replicate_id = f"replicate_{index}"

        extracted.append(
            {
                "replicate_id": replicate_id,
                "seed": seed,
                "generated_at": str(raw.get("generated_at", "")),
                "config": config,
                "runs": runs,
            }
        )

    return extracted or [_materialize_legacy_replicate(results_payload)]


def results_replicate_count(results_payload: dict[str, Any]) -> int:
    return len(extract_replicates(results_payload))


def analysis_required_for_results(results_payload: dict[str, Any]) -> bool:
    return results_replicate_count(results_payload) > 1


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_seed(*parts: Any) -> int:
    material = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _derive_base_bootstrap_seed(replicates: list[dict[str, Any]]) -> int:
    seeds = [str(_safe_int(row.get("seed")) or 0) for row in replicates]
    return _hash_seed("analysis", ",".join(seeds)) & 0x7FFFFFFF


def _group_keys_for_replicate(replicate: dict[str, Any]) -> list[dict[str, Any]]:
    config = replicate.get("config", {}) if isinstance(replicate.get("config"), dict) else {}
    runs = replicate.get("runs", []) if isinstance(replicate.get("runs"), list) else []
    run_modes = _normalize_run_modes(config, runs)

    workers: list[str] = []
    worker_models = config.get("worker_models", [])
    if isinstance(worker_models, list):
        for worker in worker_models:
            if isinstance(worker, str) and worker and worker not in workers:
                workers.append(worker)
    for run in runs:
        worker = run.get("worker_model")
        if isinstance(worker, str) and worker and worker not in workers:
            workers.append(worker)

    mentors_by_worker: dict[str, list[str]] = {worker: [] for worker in workers}
    mentor_models = config.get("mentor_models", [])
    if isinstance(mentor_models, list):
        for worker in workers:
            for mentor in mentor_models:
                if isinstance(mentor, str) and mentor and mentor not in mentors_by_worker[worker]:
                    mentors_by_worker[worker].append(mentor)

    for run in runs:
        if run.get("mode") != "mentor_worker":
            continue
        worker = run.get("worker_model")
        mentor = run.get("mentor_model")
        if not isinstance(worker, str) or not worker:
            continue
        if worker not in mentors_by_worker:
            mentors_by_worker[worker] = []
        if isinstance(mentor, str) and mentor and mentor not in mentors_by_worker[worker]:
            mentors_by_worker[worker].append(mentor)

    timeout = _safe_int(config.get("timeout_seconds"))
    repro_mode = _safe_bool(config.get("repro_mode"))
    task_pack = str(config.get("task_pack", ""))
    suite = str(config.get("suite", ""))
    max_turns = _safe_int(config.get("max_turns"))

    keys: list[dict[str, Any]] = []
    for worker in sorted(workers):
        mentors = sorted(mentors_by_worker.get(worker, []))
        if mentors:
            for mentor in mentors:
                keys.append(
                    {
                        "task_pack": task_pack,
                        "suite": suite,
                        "worker_model": worker,
                        "mentor_model": mentor,
                        "run_modes": list(run_modes),
                        "max_turns": max_turns,
                        "timeout_seconds": timeout,
                        "repro_mode": repro_mode,
                    }
                )
        else:
            keys.append(
                {
                    "task_pack": task_pack,
                    "suite": suite,
                    "worker_model": worker,
                    "mentor_model": "",
                    "run_modes": list(run_modes),
                    "max_turns": max_turns,
                    "timeout_seconds": timeout,
                    "repro_mode": repro_mode,
                }
            )
    return keys


def _resampling_unit_id(run: dict[str, Any]) -> str | None:
    family_id = run.get("task_family_id")
    if isinstance(family_id, str) and family_id:
        return family_id
    task_id = run.get("task_id")
    if isinstance(task_id, str) and task_id:
        return task_id
    return None


def _resampling_unit_outcomes_for_mode(
    *,
    runs: list[dict[str, Any]],
    mode: str,
    worker_model: str,
    mentor_model: str,
) -> dict[str, float]:
    by_unit: dict[str, list[float]] = {}
    for run in runs:
        if run.get("mode") != mode:
            continue
        worker = run.get("worker_model")
        if not isinstance(worker, str) or worker != worker_model:
            continue
        if mode == "mentor_worker":
            mentor = run.get("mentor_model")
            if not isinstance(mentor, str) or mentor != mentor_model:
                continue
        unit_id = _resampling_unit_id(run)
        if unit_id is None:
            continue
        passed = run.get("pass")
        if not isinstance(passed, bool):
            continue
        by_unit.setdefault(unit_id, []).append(1.0 if passed else 0.0)

    return {unit_id: mean(values) for unit_id, values in by_unit.items() if values}


def _percentile(sorted_values: list[float], quantile: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * quantile
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return sorted_values[lower]
    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    return lower_value + (upper_value - lower_value) * (position - lower)


def _ci_bounds(distribution: list[float]) -> tuple[float | None, float | None]:
    if not distribution:
        return (None, None)
    ordered = sorted(distribution)
    return (_percentile(ordered, 0.025), _percentile(ordered, 0.975))


def _bootstrap_mode_distribution(
    *,
    replicate_outcomes: list[dict[str, float]],
    bootstrap_samples: int,
    seed: int,
) -> list[float]:
    rng = random.Random(seed)
    distribution: list[float] = []
    for _ in range(bootstrap_samples):
        pooled: list[float] = []
        for outcomes in replicate_outcomes:
            values = list(outcomes.values())
            if not values:
                continue
            sample = [values[rng.randrange(len(values))] for _ in range(len(values))]
            pooled.append(mean(sample))
        if pooled:
            distribution.append(mean(pooled))
    return distribution


def _bootstrap_paired_lift_distribution(
    *,
    replicate_diffs: list[list[float]],
    bootstrap_samples: int,
    seed: int,
) -> list[float]:
    rng = random.Random(seed)
    distribution: list[float] = []
    for _ in range(bootstrap_samples):
        pooled: list[float] = []
        for diffs in replicate_diffs:
            if not diffs:
                continue
            sample = [diffs[rng.randrange(len(diffs))] for _ in range(len(diffs))]
            pooled.append(mean(sample))
        if pooled:
            distribution.append(mean(pooled))
    return distribution


def _two_sided_pvalue(distribution: list[float]) -> float | None:
    if not distribution:
        return None
    n = len(distribution)
    less_equal_zero = sum(1 for value in distribution if value <= 0.0) / n
    greater_equal_zero = sum(1 for value in distribution if value >= 0.0) / n
    return min(1.0, 2.0 * min(less_equal_zero, greater_equal_zero))


def _one_sided_pvalue_lift_gt_zero(distribution: list[float]) -> float | None:
    if not distribution:
        return None
    # Add-one smoothing avoids returning exactly 0.0 for finite bootstrap draws.
    n = len(distribution)
    non_positive = sum(1 for value in distribution if value <= 0.0)
    return (non_positive + 1.0) / (n + 1.0)


def generate_analysis_payload(
    results_payload: dict[str, Any],
    *,
    bootstrap_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    bootstrap_seed: int | None = None,
) -> dict[str, Any]:
    if bootstrap_samples <= 0:
        raise ValueError("bootstrap_samples must be > 0")

    replicates = extract_replicates(results_payload)
    base_seed = bootstrap_seed if bootstrap_seed is not None else _derive_base_bootstrap_seed(replicates)

    grouped: dict[str, dict[str, Any]] = {}
    for replicate in replicates:
        for group_key in _group_keys_for_replicate(replicate):
            key_json = _canonical_json(group_key)
            grouped.setdefault(
                key_json,
                {
                    "group_key": group_key,
                    "replicates": [],
                },
            )["replicates"].append(replicate)

    groups_payload: list[dict[str, Any]] = []
    for key_json in sorted(grouped):
        grouped_entry = grouped[key_json]
        group_key = grouped_entry["group_key"]
        group_replicates = grouped_entry["replicates"]
        run_modes = list(group_key.get("run_modes", []))
        config_hash = hashlib.sha256(key_json.encode("utf-8")).hexdigest()
        replicate_seeds = [_safe_int(row.get("seed")) or 0 for row in group_replicates]
        group_seed = _hash_seed(base_seed, ",".join(str(seed) for seed in replicate_seeds), config_hash) & 0x7FFFFFFF

        worker_model = str(group_key.get("worker_model", ""))
        mentor_model = str(group_key.get("mentor_model", ""))

        replicate_metrics: list[dict[str, Any]] = []
        mode_outcomes: dict[str, list[dict[str, float]]] = {mode: [] for mode in run_modes}
        replicate_lifts: list[float] = []
        replicate_pair_diffs: list[list[float]] = []

        for replicate in group_replicates:
            runs = replicate.get("runs", []) if isinstance(replicate.get("runs"), list) else []

            task_outcomes_by_mode: dict[str, dict[str, float]] = {}
            pass_rates_by_mode: dict[str, float | None] = {}
            task_counts_by_mode: dict[str, int] = {}
            for mode in run_modes:
                outcomes = _resampling_unit_outcomes_for_mode(
                    runs=runs,
                    mode=mode,
                    worker_model=worker_model,
                    mentor_model=mentor_model,
                )
                task_outcomes_by_mode[mode] = outcomes
                mode_outcomes.setdefault(mode, []).append(outcomes)
                pass_rates_by_mode[mode] = mean(outcomes.values()) if outcomes else None
                task_counts_by_mode[mode] = len(outcomes)

            baseline_map = task_outcomes_by_mode.get("worker_only", {})
            mentored_map = task_outcomes_by_mode.get("mentor_worker", {})
            baseline_rate = pass_rates_by_mode.get("worker_only")
            mentored_rate = pass_rates_by_mode.get("mentor_worker")
            lift_value = None
            if baseline_rate is not None and mentored_rate is not None:
                lift_value = mentored_rate - baseline_rate
                replicate_lifts.append(lift_value)

            common_tasks = sorted(set(baseline_map).intersection(mentored_map))
            task_diffs = [mentored_map[task] - baseline_map[task] for task in common_tasks]
            if task_diffs:
                replicate_pair_diffs.append(task_diffs)

            replicate_metrics.append(
                {
                    "replicate_id": str(replicate.get("replicate_id", "")),
                    "seed": _safe_int(replicate.get("seed")) or 0,
                    "pass_rates_by_mode": {
                        mode: _round_or_none(pass_rates_by_mode.get(mode))
                        for mode in sorted(pass_rates_by_mode)
                    },
                    "effective_sample_size_by_mode": {
                        mode: int(task_counts_by_mode.get(mode, 0)) for mode in sorted(task_counts_by_mode)
                    },
                    "task_counts_by_mode": {
                        mode: int(task_counts_by_mode.get(mode, 0)) for mode in sorted(task_counts_by_mode)
                    },
                    "baseline_rate": _round_or_none(baseline_rate),
                    "mentored_rate": _round_or_none(mentored_rate),
                    "lift": _round_or_none(lift_value),
                }
            )

        mode_stats: dict[str, dict[str, Any]] = {}
        for mode in sorted(run_modes):
            per_replicate = [
                item["pass_rates_by_mode"].get(mode)
                for item in replicate_metrics
                if item["pass_rates_by_mode"].get(mode) is not None
            ]
            mean_value = mean(per_replicate) if per_replicate else None
            mode_seed = _hash_seed(group_seed, mode) & 0x7FFFFFFF
            distribution = _bootstrap_mode_distribution(
                replicate_outcomes=mode_outcomes.get(mode, []),
                bootstrap_samples=bootstrap_samples,
                seed=mode_seed,
            )
            ci_low, ci_high = _ci_bounds(distribution)
            mode_stats[mode] = {
                "mean": _round_or_none(mean_value),
                "ci_low": _round_or_none(ci_low),
                "ci_high": _round_or_none(ci_high),
                "replicate_values": [_round_or_none(value) for value in per_replicate],
            }

        baseline_stats = mode_stats.get("worker_only", {})
        mentored_stats = mode_stats.get("mentor_worker", {})

        lift_mean = mean(replicate_lifts) if replicate_lifts else None
        lift_distribution = _bootstrap_paired_lift_distribution(
            replicate_diffs=replicate_pair_diffs,
            bootstrap_samples=bootstrap_samples,
            seed=_hash_seed(group_seed, "lift") & 0x7FFFFFFF,
        )
        lift_ci_low, lift_ci_high = _ci_bounds(lift_distribution)
        lift_ci_excludes_zero = False
        if lift_ci_low is not None and lift_ci_high is not None:
            lift_ci_excludes_zero = lift_ci_low > 0.0 or lift_ci_high < 0.0
        paired_pvalue_two_sided = _two_sided_pvalue(lift_distribution)
        paired_pvalue_lift_gt_zero = _one_sided_pvalue_lift_gt_zero(lift_distribution)
        paired_significant = bool(
            paired_pvalue_lift_gt_zero is not None
            and paired_pvalue_lift_gt_zero < 0.05
            and (lift_mean or 0.0) > 0.0
        )

        groups_payload.append(
            {
                "group_key": group_key,
                "config_hash": config_hash,
                "replicate_count": len(group_replicates),
                "replicate_seeds": replicate_seeds,
                "bootstrap_seed": group_seed,
                "mode_stats": mode_stats,
                "baseline_mean": _round_or_none(_safe_float(baseline_stats.get("mean"))),
                "baseline_ci_low": _round_or_none(_safe_float(baseline_stats.get("ci_low"))),
                "baseline_ci_high": _round_or_none(_safe_float(baseline_stats.get("ci_high"))),
                "mentored_mean": _round_or_none(_safe_float(mentored_stats.get("mean"))),
                "mentored_ci_low": _round_or_none(_safe_float(mentored_stats.get("ci_low"))),
                "mentored_ci_high": _round_or_none(_safe_float(mentored_stats.get("ci_high"))),
                "lift_mean": _round_or_none(lift_mean),
                "lift_ci_low": _round_or_none(lift_ci_low),
                "lift_ci_high": _round_or_none(lift_ci_high),
                "lift_ci_excludes_zero": lift_ci_excludes_zero,
                "lift_significant": lift_ci_excludes_zero,
                "lift_p_value_gt_zero": _round_or_none(paired_pvalue_lift_gt_zero, 8),
                "paired_significance": {
                    "method": PAIRED_SIGNIFICANCE_METHOD,
                    "significant": paired_significant,
                    "p_value_two_sided": _round_or_none(paired_pvalue_two_sided, 8),
                    "p_value_lift_gt_zero": _round_or_none(paired_pvalue_lift_gt_zero, 8),
                    "ci_low": _round_or_none(lift_ci_low),
                    "ci_high": _round_or_none(lift_ci_high),
                    "unit_pair_count": int(sum(len(item) for item in replicate_pair_diffs)),
                    "task_pair_count": int(sum(len(item) for item in replicate_pair_diffs)),
                },
                "replicate_metrics": replicate_metrics,
            }
        )

    return {
        "analysis_version": ANALYSIS_VERSION,
        # Deterministic provenance timestamp anchored to results payload.
        "generated_at": str(results_payload.get("generated_at", "")),
        "ci_method": CI_METHOD,
        "bootstrap_samples": int(bootstrap_samples),
        "bootstrap_seed": int(base_seed),
        "group_count": len(groups_payload),
        "groups": groups_payload,
    }


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


def _expect_number_or_none(value: Any, path: str, errors: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"Invalid type for {path}: expected number|null, got {type(value).__name__}")


def validate_analysis_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["analysis.json must contain a JSON object"]

    _expect_type(payload, "analysis_version", str, "analysis", errors)
    _expect_type(payload, "ci_method", str, "analysis", errors)
    bootstrap_samples = _expect_type(payload, "bootstrap_samples", int, "analysis", errors)
    _expect_type(payload, "bootstrap_seed", int, "analysis", errors)
    groups = _expect_type(payload, "groups", list, "analysis", errors)

    if isinstance(bootstrap_samples, int) and bootstrap_samples <= 0:
        errors.append("analysis.bootstrap_samples must be > 0")

    if isinstance(groups, list):
        for index, item in enumerate(groups):
            if not isinstance(item, dict):
                errors.append(f"analysis.groups[{index}] must be an object")
                continue
            path = f"analysis.groups[{index}]"
            _expect_type(item, "group_key", dict, path, errors)
            _expect_type(item, "replicate_count", int, path, errors)
            _expect_type(item, "replicate_seeds", list, path, errors)
            _expect_type(item, "mode_stats", dict, path, errors)

            for numeric_field in (
                "baseline_mean",
                "baseline_ci_low",
                "baseline_ci_high",
                "mentored_mean",
                "mentored_ci_low",
                "mentored_ci_high",
                "lift_mean",
                "lift_ci_low",
                "lift_ci_high",
            ):
                _expect_number_or_none(item.get(numeric_field), f"{path}.{numeric_field}", errors)

            lift_significant = item.get("lift_significant")
            if lift_significant is not None and not isinstance(lift_significant, bool):
                errors.append(f"Invalid type for {path}.lift_significant: expected bool|null")

            paired = item.get("paired_significance")
            if paired is not None:
                if not isinstance(paired, dict):
                    errors.append(f"Invalid type for {path}.paired_significance: expected object")
                else:
                    method = paired.get("method")
                    if not isinstance(method, str):
                        errors.append(f"Invalid type for {path}.paired_significance.method: expected str")
                    significant = paired.get("significant")
                    if significant is not None and not isinstance(significant, bool):
                        errors.append(
                            f"Invalid type for {path}.paired_significance.significant: expected bool|null"
                        )
                    for paired_numeric in ("p_value_two_sided", "ci_low", "ci_high"):
                        _expect_number_or_none(
                            paired.get(paired_numeric),
                            f"{path}.paired_significance.{paired_numeric}",
                            errors,
                        )
                    _expect_number_or_none(
                        paired.get("p_value_lift_gt_zero"),
                        f"{path}.paired_significance.p_value_lift_gt_zero",
                        errors,
                    )

            _expect_number_or_none(
                item.get("lift_p_value_gt_zero"),
                f"{path}.lift_p_value_gt_zero",
                errors,
            )

    return errors


def select_primary_group(
    *,
    results_payload: dict[str, Any],
    analysis_payload: dict[str, Any],
) -> dict[str, Any] | None:
    groups = analysis_payload.get("groups", [])
    if not isinstance(groups, list):
        return None
    rows = [row for row in groups if isinstance(row, dict)]
    if not rows:
        return None

    aggregates = results_payload.get("aggregates", {})
    if not isinstance(aggregates, dict):
        aggregates = {}
    best_workers = aggregates.get("best_workers", [])
    best_mentors = aggregates.get("best_mentors", [])
    preferred_worker = ""
    preferred_mentor = ""
    if isinstance(best_workers, list) and best_workers and isinstance(best_workers[0], dict):
        preferred_worker = str(best_workers[0].get("worker_model", ""))
    if isinstance(best_mentors, list) and best_mentors and isinstance(best_mentors[0], dict):
        preferred_mentor = str(best_mentors[0].get("mentor_model", ""))

    def _key(row: dict[str, Any]) -> tuple[float, float, str]:
        lift = _safe_float(row.get("lift_mean")) or 0.0
        mentored = _safe_float(row.get("mentored_mean")) or 0.0
        config_hash = str(row.get("config_hash", ""))
        return (lift, mentored, config_hash)

    if preferred_worker and preferred_mentor:
        exact = [
            row
            for row in rows
            if isinstance(row.get("group_key"), dict)
            and str(row["group_key"].get("worker_model", "")) == preferred_worker
            and str(row["group_key"].get("mentor_model", "")) == preferred_mentor
        ]
        if exact:
            return sorted(exact, key=_key, reverse=True)[0]

    if preferred_worker:
        worker_rows = [
            row
            for row in rows
            if isinstance(row.get("group_key"), dict)
            and str(row["group_key"].get("worker_model", "")) == preferred_worker
        ]
        if worker_rows:
            return sorted(worker_rows, key=_key, reverse=True)[0]

    return sorted(rows, key=_key, reverse=True)[0]
