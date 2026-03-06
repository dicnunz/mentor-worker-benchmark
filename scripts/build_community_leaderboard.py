#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.analysis import (
    generate_analysis_payload,
    select_primary_group,
    validate_analysis_payload,
)
from mentor_worker_benchmark.submission import read_submission_bundle, verify_submission_bundle

HEADLINE_SUITES = {"dev", "dev50", "test"}
SANITY_SUITES = {"dev10", "quick"}
TIMEOUT_TOKEN_RE = re.compile(r"(timed out|\btimeout\b)", re.IGNORECASE)


def _safe_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _best_worker(aggregates: dict[str, Any]) -> dict[str, Any] | None:
    rows = aggregates.get("best_workers", [])
    if not isinstance(rows, list) or not rows:
        return None
    first = rows[0]
    return first if isinstance(first, dict) else None


def _best_mentor(aggregates: dict[str, Any]) -> dict[str, Any] | None:
    rows = aggregates.get("best_mentors", [])
    if not isinstance(rows, list) or not rows:
        return None
    first = rows[0]
    return first if isinstance(first, dict) else None


def _int_dict(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    output: dict[str, int] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(item, bool):
            output[key] = int(item)
        elif isinstance(item, int):
            output[key] = item
        elif isinstance(item, float):
            output[key] = int(item)
    return output


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _submission_zip_paths(submissions_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for path in submissions_dir.rglob("*.zip"):
        if not path.is_file():
            continue
        if path.name.startswith(("local_", "tmp_")):
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.as_posix())


def _seed_list_from_results(results: dict[str, Any]) -> list[int]:
    seeds: list[int] = []
    replicates = results.get("replicates")
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

    config = results.get("config", {})
    if isinstance(config, dict):
        generation = config.get("generation", {})
        if isinstance(generation, dict):
            seed = _safe_int(generation.get("seed"))
            if seed is not None:
                return [seed]
    return []


def _config_run_modes(config: dict[str, Any], runs: list[dict[str, Any]]) -> list[str]:
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


def _compute_passes_from_runs(runs: list[dict[str, Any]], modes: list[str]) -> dict[str, int]:
    counts = {mode: 0 for mode in modes}
    for run in runs:
        mode = run.get("mode")
        if not isinstance(mode, str):
            continue
        counts.setdefault(mode, 0)
        if run.get("pass") is True:
            counts[mode] += 1
    return counts


def _record_error(mode: str, message: Any, errors: dict[str, int], timeouts: dict[str, int]) -> None:
    if not isinstance(message, str) or not message.strip():
        return
    errors[mode] = errors.get(mode, 0) + 1
    if TIMEOUT_TOKEN_RE.search(message):
        timeouts[mode] = timeouts.get(mode, 0) + 1


def _compute_model_call_errors_from_runs(
    runs: list[dict[str, Any]],
    modes: list[str],
) -> tuple[dict[str, int], dict[str, int]]:
    errors_by_mode = {mode: 0 for mode in modes}
    timeouts_by_mode = {mode: 0 for mode in modes}
    for run in runs:
        mode = run.get("mode")
        if not isinstance(mode, str):
            continue
        errors_by_mode.setdefault(mode, 0)
        timeouts_by_mode.setdefault(mode, 0)

        log = run.get("log")
        if not isinstance(log, dict):
            continue

        if mode == "worker_only":
            _record_error(mode, log.get("worker_error"), errors_by_mode, timeouts_by_mode)
            continue

        turns = log.get("turns")
        if not isinstance(turns, list):
            continue
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            _record_error(mode, turn.get("worker_error"), errors_by_mode, timeouts_by_mode)
            _record_error(mode, turn.get("mentor_error"), errors_by_mode, timeouts_by_mode)

    return errors_by_mode, timeouts_by_mode


def _derive_metrics(
    *,
    summary: dict[str, Any],
    config: dict[str, Any],
    runs: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, str]]:
    metrics_source: dict[str, str] = {}
    has_runs = isinstance(runs, list)
    run_modes = _config_run_modes(config, runs) if has_runs else []

    total_runs_summary = _safe_int(summary.get("total_runs")) if "total_runs" in summary else None
    if total_runs_summary is not None:
        total_runs = total_runs_summary
        metrics_source["total_runs"] = "summary"
    elif has_runs:
        total_runs = len(runs)
        metrics_source["total_runs"] = "runs_backfill"
    else:
        total_runs = 0
        metrics_source["total_runs"] = "absent_default"

    if "passes_by_mode" in summary:
        passes_by_mode = _int_dict(summary.get("passes_by_mode"))
        metrics_source["passes_by_mode"] = "summary"
    elif has_runs:
        passes_by_mode = _compute_passes_from_runs(runs, run_modes)
        metrics_source["passes_by_mode"] = "runs_backfill"
    else:
        passes_by_mode = {}
        metrics_source["passes_by_mode"] = "absent_default"

    total_passes_summary = _safe_int(summary.get("total_passes")) if "total_passes" in summary else None
    if total_passes_summary is not None:
        total_passes = total_passes_summary
        metrics_source["total_passes"] = "summary"
    elif has_runs:
        total_passes = sum(1 for run in runs if run.get("pass") is True)
        metrics_source["total_passes"] = "runs_backfill"
    elif passes_by_mode:
        total_passes = sum(passes_by_mode.values())
        metrics_source["total_passes"] = "derived_from_modes"
    else:
        total_passes = 0
        metrics_source["total_passes"] = "absent_default"

    if "model_call_errors_by_mode" in summary:
        model_call_errors_by_mode = _int_dict(summary.get("model_call_errors_by_mode"))
        metrics_source["model_call_errors_by_mode"] = "summary"
    elif has_runs:
        model_call_errors_by_mode, _ = _compute_model_call_errors_from_runs(runs, run_modes)
        metrics_source["model_call_errors_by_mode"] = "runs_backfill"
    else:
        model_call_errors_by_mode = {}
        metrics_source["model_call_errors_by_mode"] = "absent_default"

    if "model_call_timeouts_by_mode" in summary:
        model_call_timeouts_by_mode = _int_dict(summary.get("model_call_timeouts_by_mode"))
        metrics_source["model_call_timeouts_by_mode"] = "summary"
    elif has_runs:
        _, model_call_timeouts_by_mode = _compute_model_call_errors_from_runs(runs, run_modes)
        metrics_source["model_call_timeouts_by_mode"] = "runs_backfill"
    else:
        model_call_timeouts_by_mode = {}
        metrics_source["model_call_timeouts_by_mode"] = "absent_default"

    total_errors_summary = (
        _safe_int(summary.get("total_model_call_errors")) if "total_model_call_errors" in summary else None
    )
    if total_errors_summary is not None:
        total_model_call_errors = total_errors_summary
        metrics_source["total_model_call_errors"] = "summary"
    else:
        total_model_call_errors = sum(model_call_errors_by_mode.values())
        source = metrics_source["model_call_errors_by_mode"]
        metrics_source["total_model_call_errors"] = (
            "derived_from_modes" if source == "summary" else source
        )

    total_timeouts_summary = (
        _safe_int(summary.get("total_model_call_timeouts"))
        if "total_model_call_timeouts" in summary
        else None
    )
    if total_timeouts_summary is not None:
        total_model_call_timeouts = total_timeouts_summary
        metrics_source["total_model_call_timeouts"] = "summary"
    else:
        total_model_call_timeouts = sum(model_call_timeouts_by_mode.values())
        source = metrics_source["model_call_timeouts_by_mode"]
        metrics_source["total_model_call_timeouts"] = (
            "derived_from_modes" if source == "summary" else source
        )

    metrics = {
        "total_runs": total_runs,
        "total_passes": total_passes,
        "passes_by_mode": passes_by_mode,
        "model_call_errors_by_mode": model_call_errors_by_mode,
        "model_call_timeouts_by_mode": model_call_timeouts_by_mode,
        "total_model_call_errors": total_model_call_errors,
        "total_model_call_timeouts": total_model_call_timeouts,
    }
    return metrics, metrics_source


def _is_official(submission_stem: str, manifest: dict[str, Any]) -> bool:
    if isinstance(manifest.get("official_submission"), bool):
        return bool(manifest["official_submission"])
    return submission_stem.startswith("official_")


def _normalize_submission(submission_path: Path) -> dict[str, Any]:
    bundle = read_submission_bundle(submission_path)
    results = bundle["results"]
    manifest = bundle["manifest"]
    environment = bundle["environment"]
    analysis_payload = bundle.get("analysis")

    config = results.get("config", {}) if isinstance(results, dict) else {}
    summary = results.get("summary", {}) if isinstance(results, dict) else {}
    aggregates = results.get("aggregates", {}) if isinstance(results, dict) else {}
    runs = results.get("runs", []) if isinstance(results.get("runs"), list) else []

    stem = submission_path.stem
    official = _is_official(stem, manifest if isinstance(manifest, dict) else {})
    label = "official" if official else "community (not official)"
    suite = str(config.get("suite", ""))
    suite_token = _normalize_suite(suite)
    if official and suite_token in HEADLINE_SUITES:
        official_role = "headline"
    elif official and suite_token in SANITY_SUITES:
        official_role = "sanity"
    elif official:
        official_role = "other"
    else:
        official_role = "community"

    best_worker = _best_worker(aggregates if isinstance(aggregates, dict) else {})
    best_mentor = _best_mentor(aggregates if isinstance(aggregates, dict) else {})
    protocol_version = str(manifest.get("protocol_version", "legacy"))
    protocol_seeds = (
        [int(item) for item in manifest.get("protocol_seeds", []) if isinstance(item, int)]
        if isinstance(manifest.get("protocol_seeds"), list)
        else []
    )
    if not protocol_seeds:
        protocol_seeds = _seed_list_from_results(results if isinstance(results, dict) else {})
    compute_budget = results.get("compute_budget", {}) if isinstance(results, dict) else {}
    if not isinstance(compute_budget, dict):
        compute_budget = {}
    time_total_s = _safe_float(
        compute_budget.get("total_wall_time_seconds", summary.get("benchmark_wall_time_seconds", 0.0))
    )
    derived_metrics, metrics_source = _derive_metrics(
        summary=summary if isinstance(summary, dict) else {},
        config=config if isinstance(config, dict) else {},
        runs=runs,
    )

    if isinstance(analysis_payload, dict):
        analysis_errors = validate_analysis_payload(analysis_payload)
        if analysis_errors:
            analysis_payload = generate_analysis_payload(results if isinstance(results, dict) else {})
    else:
        analysis_payload = generate_analysis_payload(results if isinstance(results, dict) else {})

    primary_group = select_primary_group(
        results_payload=results if isinstance(results, dict) else {},
        analysis_payload=analysis_payload,
    )
    if not isinstance(primary_group, dict):
        primary_group = {}

    def _metric_or_default(value: Any, default: float) -> float:
        metric = _safe_float(value)
        return metric if metric is not None else default

    baseline_mean = round(
        _metric_or_default(
            primary_group.get("baseline_mean"),
            _safe_float(best_worker.get("baseline_pass_rate", 0.0)) if isinstance(best_worker, dict) else 0.0,
        ),
        4,
    )
    mentored_mean = round(
        _metric_or_default(
            primary_group.get("mentored_mean"),
            _safe_float(best_worker.get("mentored_pass_rate", 0.0)) if isinstance(best_worker, dict) else 0.0,
        ),
        4,
    )
    lift_mean = round(
        _metric_or_default(
            primary_group.get("lift_mean"),
            _safe_float(best_worker.get("delta", 0.0)) if isinstance(best_worker, dict) else 0.0,
        ),
        4,
    )
    baseline_ci_low = round(_metric_or_default(primary_group.get("baseline_ci_low"), baseline_mean), 4)
    baseline_ci_high = round(_metric_or_default(primary_group.get("baseline_ci_high"), baseline_mean), 4)
    mentored_ci_low = round(_metric_or_default(primary_group.get("mentored_ci_low"), mentored_mean), 4)
    mentored_ci_high = round(_metric_or_default(primary_group.get("mentored_ci_high"), mentored_mean), 4)
    lift_ci_low = round(_metric_or_default(primary_group.get("lift_ci_low"), lift_mean), 4)
    lift_ci_high = round(_metric_or_default(primary_group.get("lift_ci_high"), lift_mean), 4)
    lift_ci_excludes_zero = lift_ci_low > 0.0 or lift_ci_high < 0.0
    if isinstance(primary_group.get("lift_significant"), bool):
        lift_significant = bool(primary_group.get("lift_significant"))
    else:
        lift_significant = lift_ci_excludes_zero
    lift_p_value_gt_zero = _safe_float(primary_group.get("lift_p_value_gt_zero"))
    if lift_p_value_gt_zero is None:
        paired = primary_group.get("paired_significance")
        if isinstance(paired, dict):
            lift_p_value_gt_zero = _safe_float(paired.get("p_value_lift_gt_zero"))

    return {
        "submission_id": stem,
        "submission_file": submission_path.name,
        "submission_path": str(submission_path.as_posix()),
        "official_submission": official,
        "submission_label": label,
        "official_role": official_role,
        "task_pack": str(manifest.get("task_pack", config.get("task_pack", ""))),
        "task_pack_version": str(manifest.get("task_pack_version", "")),
        "suite": suite,
        "generated_at": str(results.get("generated_at", "")),
        "manifest_created_at": str(manifest.get("created_at", "")),
        "verified_at": str(manifest.get("created_at", "") or results.get("generated_at", "")),
        "git_commit_hash": str(manifest.get("git_commit_hash", "")),
        "cli_command": str(manifest.get("cli_command", "")),
        "models": list(config.get("models", [])) if isinstance(config.get("models"), list) else [],
        "worker_models": (
            list(config.get("worker_models", [])) if isinstance(config.get("worker_models"), list) else []
        ),
        "run_modes": list(config.get("run_modes", [])) if isinstance(config.get("run_modes"), list) else [],
        "protocol_version": protocol_version,
        "seeds_count": len(protocol_seeds),
        "protocol_seeds": protocol_seeds,
        "time_total_s": round(time_total_s, 4),
        "total_runs": int(derived_metrics["total_runs"]),
        "total_passes": int(derived_metrics["total_passes"]),
        "passes_by_mode": dict(derived_metrics["passes_by_mode"]),
        "benchmark_wall_time_seconds": round(_safe_float(summary.get("benchmark_wall_time_seconds", 0.0)), 4),
        "violation_count": int(summary.get("violation_count", 0)),
        "model_call_errors_by_mode": dict(derived_metrics["model_call_errors_by_mode"]),
        "model_call_timeouts_by_mode": dict(derived_metrics["model_call_timeouts_by_mode"]),
        "total_model_call_errors": int(derived_metrics["total_model_call_errors"]),
        "total_model_call_timeouts": int(derived_metrics["total_model_call_timeouts"]),
        "metrics_source": metrics_source,
        "benchmark_version": str(environment.get("benchmark_version", "")),
        "baseline_mean": baseline_mean,
        "baseline_ci_low": baseline_ci_low,
        "baseline_ci_high": baseline_ci_high,
        "mentored_mean": mentored_mean,
        "mentored_ci_low": mentored_ci_low,
        "mentored_ci_high": mentored_ci_high,
        "lift_mean": lift_mean,
        "lift_ci_low": lift_ci_low,
        "lift_ci_high": lift_ci_high,
        "lift_significant": lift_significant,
        "lift_p_value_gt_zero": round(lift_p_value_gt_zero, 8)
        if isinstance(lift_p_value_gt_zero, float)
        else None,
        "best_worker": {
            "worker_model": str(best_worker.get("worker_model", "")) if isinstance(best_worker, dict) else "",
            # Keep legacy fields but map to analysis means for backward-compatible UI consumers.
            "baseline_pass_rate": baseline_mean,
            "mentored_pass_rate": mentored_mean,
            "control_pass_rate": round(
                _safe_float(best_worker.get("control_pass_rate", 0.0)) if isinstance(best_worker, dict) else 0.0,
                4,
            ),
            "lift": lift_mean,
        },
        "best_mentor": {
            "mentor_model": str(best_mentor.get("mentor_model", "")) if isinstance(best_mentor, dict) else "",
            "avg_lift_across_workers": round(
                _safe_float(best_mentor.get("avg_lift_across_workers", 0.0))
                if isinstance(best_mentor, dict)
                else 0.0,
                4,
            ),
            "overall_mentored_pass_rate": round(
                _safe_float(best_mentor.get("overall_mentored_pass_rate", 0.0))
                if isinstance(best_mentor, dict)
                else 0.0,
                4,
            ),
            "mentor_violation_rate": round(
                _safe_float(best_mentor.get("mentor_violation_rate", 0.0))
                if isinstance(best_mentor, dict)
                else 0.0,
                4,
            ),
        },
    }


def _sort_key(entry: dict[str, Any]) -> tuple[str, str]:
    return (str(entry.get("generated_at", "")), str(entry.get("submission_id", "")))


def _normalize_suite(value: Any) -> str:
    raw = str(value or "").strip()
    if raw in {"quick", "dev", "dev10", "dev50", "test"}:
        return raw
    if not raw:
        return "unknown"
    return "mixed"


def _suite_priority(suite: str) -> int:
    priorities = {
        "dev": 0,
        "dev50": 1,
        "test": 2,
        "dev10": 3,
        "quick": 4,
        "mixed": 5,
        "unknown": 6,
    }
    return priorities.get(suite, 6)


def _to_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2%}"
    return ""


def _headline_official_runs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pack: dict[str, list[dict[str, Any]]] = {}
    for row in entries:
        if row.get("official_role") != "headline":
            continue
        by_pack.setdefault(str(row.get("task_pack", "")), []).append(row)

    rows: list[dict[str, Any]] = []
    for _, pack_rows in by_pack.items():
        ordered = sorted(pack_rows, key=_sort_key, reverse=True)
        best = min(
            ordered,
            key=lambda item: _suite_priority(_normalize_suite(item.get("suite"))),
        )
        rows.append(best)

    rows.sort(key=lambda item: _sort_key(item), reverse=True)
    rows.sort(key=lambda item: _suite_priority(_normalize_suite(item.get("suite"))))
    return rows


def _sanity_official_runs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in entries if row.get("official_role") == "sanity"]
    rows.sort(key=_sort_key, reverse=True)
    rows.sort(key=lambda item: _suite_priority(_normalize_suite(item.get("suite"))))
    return rows


def _write_markdown(entries: list[dict[str, Any]], output_path: Path, generated_at: str) -> None:
    official_rows = _headline_official_runs(entries)
    sanity_rows = _sanity_official_runs(entries)

    lines = [
        "# Community Leaderboard",
        "",
        f"Generated: {generated_at}",
        "",
        "## Headline Official Baselines",
        "",
        "Policy: headline official baselines come from `dev`/`dev50`/`test` suites. "
        "`dev10`/`quick` official runs are sanity runs for harness health.",
        "",
        "| Submission | Pack | Suite | Top Worker | Baseline | Mentored | Lift |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    if official_rows:
        for row in official_rows:
            worker = row.get("best_worker", {})
            lines.append(
                f"| {row.get('submission_id')} | {row.get('task_pack')} | {row.get('suite')} | "
                f"{worker.get('worker_model', '')} | {_to_percent(worker.get('baseline_pass_rate', 0.0))} | "
                f"{_to_percent(worker.get('mentored_pass_rate', 0.0))} | {_to_percent(worker.get('lift', 0.0))} |"
            )
    else:
        lines.append("| (none) | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Official Sanity Runs",
            "",
            "| Submission | Pack | Suite | Top Worker | Baseline | Mentored | Model Errors | Timeouts |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if sanity_rows:
        for row in sanity_rows:
            worker = row.get("best_worker", {})
            lines.append(
                f"| {row.get('submission_id')} | {row.get('task_pack')} | {row.get('suite')} | "
                f"{worker.get('worker_model', '')} | {_to_percent(worker.get('baseline_pass_rate', 0.0))} | "
                f"{_to_percent(worker.get('mentored_pass_rate', 0.0))} | "
                f"{row.get('total_model_call_errors', 0)} | {row.get('total_model_call_timeouts', 0)} |"
            )
    else:
        lines.append("| (none) | - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## All Verified Submissions",
            "",
            "| Submission | Label | Role | Pack | Suite | Top Worker | Baseline | Mentored | Model Errors | Timeouts | Metrics Source | Commit |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(entries, key=_sort_key, reverse=True):
        worker = row.get("best_worker", {})
        metrics_source = row.get("metrics_source", {})
        total_passes_src = (
            metrics_source.get("total_passes", "")
            if isinstance(metrics_source, dict)
            else ""
        )
        errors_src = (
            metrics_source.get("total_model_call_errors", "")
            if isinstance(metrics_source, dict)
            else ""
        )
        source_label = ",".join(part for part in [str(total_passes_src), str(errors_src)] if part)
        lines.append(
            f"| {row.get('submission_id')} | {row.get('submission_label')} | {row.get('official_role')} | {row.get('task_pack')} | "
            f"{row.get('suite')} | {worker.get('worker_model', '')} | "
            f"{_to_percent(worker.get('baseline_pass_rate', 0.0))} | "
            f"{_to_percent(worker.get('mentored_pass_rate', 0.0))} | "
            f"{row.get('total_model_call_errors', 0)} | {row.get('total_model_call_timeouts', 0)} | "
            f"{source_label or '-'} | {row.get('git_commit_hash')} |"
        )
    if not entries:
        lines.append("| (none) | - | - | - | - | - | - | - | - | - | - | - |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_index_html(summary: dict[str, Any], output_path: Path) -> None:
    summary_json = json.dumps(summary, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    generated_at = html.escape(str(summary.get("generated_at", "")))
    official_count = int(summary.get("official_count", 0))
    community_count = int(summary.get("community_count", 0))
    total_count = int(summary.get("submission_count", 0))

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mentor Worker Benchmark Leaderboard</title>
  <style>
    :root {{
      --bg: #f3f6fb;
      --card: #ffffff;
      --text: #1d2433;
      --muted: #5b6782;
      --line: #dbe2ef;
      --accent: #0c5ab9;
      --warn: #b45309;
      --ok: #0f766e;
      --chip: #eef3fb;
      --stripe: #fbfcff;
    }}
    body {{
      margin: 0;
      font-family: "SF Pro Text", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 0% 0%, #e9f0fd 0, var(--bg) 52%);
      color: var(--text);
    }}
    main {{
      max-width: 1240px;
      margin: 0 auto;
      padding: 1.25rem 1rem 2rem;
    }}
    h1 {{
      margin: 0;
      font-size: 1.8rem;
      line-height: 1.2;
    }}
    h2 {{
      margin: 0 0 0.55rem;
      font-size: 1.08rem;
    }}
    p {{
      margin: 0.35rem 0;
      line-height: 1.4;
    }}
    .meta {{
      color: var(--muted);
      margin-top: 0.4rem;
      margin-bottom: 0.9rem;
      font-size: 0.9rem;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 0.9rem;
      margin-bottom: 0.9rem;
      box-shadow: 0 2px 10px rgba(15, 34, 68, 0.06);
      overflow: hidden;
    }}
    .intro p {{
      max-width: 90ch;
      font-size: 0.92rem;
    }}
    .glossary {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.38rem;
      margin-top: 0.55rem;
    }}
    .term {{
      position: relative;
      border: 1px solid var(--line);
      background: var(--chip);
      border-radius: 999px;
      padding: 0.14rem 0.55rem;
      font-size: 0.78rem;
      color: var(--muted);
      cursor: help;
      white-space: nowrap;
    }}
    .term::after {{
      content: attr(data-tip);
      position: absolute;
      left: 50%;
      bottom: calc(100% + 7px);
      transform: translateX(-50%);
      max-width: 240px;
      width: max-content;
      white-space: normal;
      text-align: left;
      background: #172033;
      color: #fff;
      border-radius: 6px;
      padding: 0.35rem 0.45rem;
      font-size: 0.72rem;
      line-height: 1.3;
      opacity: 0;
      pointer-events: none;
      transition: opacity 120ms ease;
      z-index: 4;
      box-shadow: 0 3px 12px rgba(0, 0, 0, 0.25);
    }}
    .term:hover::after,
    .term:focus-visible::after {{
      opacity: 1;
    }}
    .toolbar {{
      display: grid;
      gap: 0.65rem;
      margin-bottom: 0.65rem;
    }}
    .tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
    }}
    .tab {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 999px;
      padding: 0.25rem 0.6rem;
      font-size: 0.82rem;
      color: var(--muted);
      cursor: pointer;
      line-height: 1.2;
    }}
    .tab.active {{
      border-color: #98b9ec;
      background: #edf4ff;
      color: #1f3a68;
      font-weight: 600;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 0.45rem 0.6rem;
      align-items: end;
    }}
    label {{
      color: var(--muted);
      font-size: 0.76rem;
      display: grid;
      gap: 0.2rem;
      min-width: 0;
    }}
    select, input[type="search"] {{
      padding: 0.32rem 0.5rem;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      font-size: 0.84rem;
      min-width: 0;
    }}
    .highlights {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.52rem;
      margin-bottom: 0.6rem;
    }}
    .hl-card {{
      border: 1px solid var(--line);
      border-radius: 10px;
      background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
      padding: 0.55rem 0.62rem;
      min-width: 0;
    }}
    .hl-label {{
      color: var(--muted);
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.02em;
      margin-bottom: 0.18rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .hl-worker {{
      font-size: 0.86rem;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .hl-value {{
      font-size: 1rem;
      font-weight: 700;
      margin-top: 0.18rem;
      font-variant-numeric: tabular-nums;
    }}
    .hl-sub {{
      margin-top: 0.22rem;
      font-size: 0.72rem;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .table-wrap {{
      border: 1px solid var(--line);
      border-radius: 10px;
      overflow: hidden;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      table-layout: fixed;
      font-size: 0.8rem;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 0.34rem 0.42rem;
      vertical-align: middle;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.25;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      position: sticky;
      top: 0;
      z-index: 2;
      background: #f7f9fd;
      font-size: 0.73rem;
      text-transform: uppercase;
      letter-spacing: 0.01em;
    }}
    tbody tr:nth-child(even) {{
      background: var(--stripe);
    }}
    .num {{
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-feature-settings: "tnum";
    }}
    .text-clip {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .badge {{
      display: inline-block;
      padding: 0.15rem 0.42rem;
      border-radius: 999px;
      font-size: 0.7rem;
      font-weight: 600;
      border: 1px solid transparent;
      line-height: 1.2;
    }}
    .badge-headline {{
      color: var(--ok);
      border-color: #9ce9dd;
      background: #ecfdf8;
    }}
    .badge-sanity {{
      color: #8a4b0f;
      border-color: #f4d6a2;
      background: #fff7ed;
    }}
    .badge-community {{
      color: #334155;
      border-color: #cbd5e1;
      background: #f8fafc;
    }}
    .badge-other {{
      color: var(--ok);
      border-color: #cce4ff;
      background: #eef6ff;
    }}
    .commit-wrap {{
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      max-width: 100%;
    }}
    .copy-btn {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 6px;
      font-size: 0.68rem;
      color: var(--muted);
      padding: 0.05rem 0.32rem;
      cursor: pointer;
      line-height: 1.2;
      flex: 0 0 auto;
    }}
    .copy-btn:hover {{
      border-color: #a5b5cf;
      color: #24324f;
    }}
    .subtle {{
      color: var(--muted);
      font-size: 0.76rem;
    }}
    .small {{
      color: var(--muted);
      font-size: 0.8rem;
      margin-top: 0.48rem;
    }}
    .metric {{
      display: inline-flex;
      align-items: center;
      gap: 0.2rem;
      max-width: 100%;
    }}
    .sig-marker {{
      display: inline-block;
      padding: 0.02rem 0.2rem;
      border-radius: 4px;
      border: 1px solid #86a7d9;
      color: #1f3a68;
      font-size: 0.64rem;
      line-height: 1.1;
      font-weight: 700;
      background: #eef4ff;
      margin-left: 0.2rem;
      vertical-align: middle;
      cursor: help;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 1080px) {{
      .controls {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .highlights {{
        grid-template-columns: 1fr;
      }}
      th, td {{
        padding: 0.3rem 0.34rem;
        font-size: 0.76rem;
      }}
    }}
    @media (max-width: 680px) {{
      .controls {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 1.48rem;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Mentor Worker Benchmark Leaderboard</h1>
    <p class="meta">
      Generated: {generated_at} |
      Submissions: {total_count} |
      Official: {official_count} |
      Community: {community_count}
    </p>

    <section class="card intro">
      <h2>What This Measures</h2>
      <p>This benchmark asks one question: does mentor guidance help a worker model solve objective coding tasks scored by tests?</p>
      <p><strong>Baseline</strong> and <strong>Mentored</strong> are means across replicates with task-family bootstrap confidence intervals.</p>
      <p><strong>Lift</strong> is mentored minus baseline, with a paired task-family bootstrap CI and a <code>sig</code> marker when CI excludes 0.</p>
      <p><strong>Errors</strong> and <strong>Timeouts</strong> count model-call failures; sanity runs focus on harness health and are not headline performance claims.</p>
      <p class="subtle">Hover glossary chips for plain-English definitions.</p>
      <div class="glossary">
        <span class="term" tabindex="0" data-tip="Mean worker-only pass rate across replicates with 95% CI.">Baseline</span>
        <span class="term" tabindex="0" data-tip="Mean pass rate with mentor guidance across replicates with 95% CI.">Mentored</span>
        <span class="term" tabindex="0" data-tip="Mentored minus baseline mean; 'sig' means 95% CI excludes 0.">Lift</span>
        <span class="term" tabindex="0" data-tip="Model call failures (bad responses, request failures, etc.).">Model errors</span>
        <span class="term" tabindex="0" data-tip="Model calls that exceeded the configured timeout.">Timeouts</span>
        <span class="term" tabindex="0" data-tip="Task pack version used for the run (for example task_pack_v2).">Pack</span>
        <span class="term" tabindex="0" data-tip="Task subset used for evaluation (for example dev50 or quick).">Suite</span>
      </div>
    </section>

    <section class="card">
      <h2>Leaderboard</h2>
      <div class="toolbar">
        <div class="tabs" role="tablist" aria-label="Role filter tabs">
          <button class="tab" data-role="headline" type="button">Headline</button>
          <button class="tab" data-role="sanity" type="button">Sanity</button>
          <button class="tab" data-role="community" type="button">Community</button>
          <button class="tab active" data-role="all" type="button">All</button>
        </div>
        <div class="controls">
          <label for="packFilter">Pack
            <select id="packFilter">
              <option value="all">all</option>
              <option value="task_pack_v1">task_pack_v1</option>
              <option value="task_pack_v2">task_pack_v2</option>
            </select>
          </label>
          <label for="suiteFilter">Suite
            <select id="suiteFilter">
              <option value="all">all</option>
              <option value="dev50">dev50</option>
              <option value="dev">dev</option>
              <option value="test">test</option>
              <option value="dev10">dev10</option>
              <option value="quick">quick</option>
              <option value="mixed">mixed</option>
              <option value="unknown">unknown</option>
            </select>
          </label>
          <label for="searchFilter">Search
            <input id="searchFilter" type="search" placeholder="submission, model, commit..." />
          </label>
          <label for="sortControl">Sort
            <select id="sortControl">
              <option value="lift_desc">Lift (high to low)</option>
              <option value="baseline_desc">Baseline (high to low)</option>
              <option value="mentored_desc">Mentored (high to low)</option>
              <option value="reliability_asc">Reliability (fewest errors/timeouts)</option>
            </select>
          </label>
        </div>
      </div>

      <div id="highlights" class="highlights"></div>

      <div class="table-wrap">
        <table>
          <colgroup>
            <col style="width: 16%" />
            <col style="width: 8%" />
            <col style="width: 9%" />
            <col style="width: 7%" />
            <col style="width: 14%" />
            <col style="width: 7%" />
            <col style="width: 7%" />
            <col style="width: 7%" />
            <col style="width: 8%" />
            <col style="width: 8%" />
            <col style="width: 9%" />
          </colgroup>
          <thead>
            <tr>
              <th>Submission</th>
              <th>Role</th>
              <th>Pack</th>
              <th>Suite</th>
              <th>Top Worker</th>
              <th class="num">Baseline</th>
              <th class="num">Mentored</th>
              <th class="num">Lift</th>
              <th class="num">Errors</th>
              <th class="num">Timeouts</th>
              <th>Commit</th>
            </tr>
          </thead>
          <tbody id="leaderRows"></tbody>
        </table>
      </div>
      <p class="small">Headline rows are baseline performance numbers. Sanity rows are harness-health checks.</p>
    </section>

    <p class="meta">Raw normalized summaries: <a href="../leaderboard/summary.json">leaderboard/summary.json</a> | Markdown: <a href="./leaderboard.md">docs/leaderboard.md</a></p>
  </main>
  <script id="summary-json" type="application/json">{summary_json}</script>
  <script>
    const summaryPayload = JSON.parse(document.getElementById("summary-json").textContent || "{{}}");
    const entries = Array.isArray(summaryPayload.entries) ? summaryPayload.entries : [];
    const tabs = Array.from(document.querySelectorAll(".tab"));
    const packFilter = document.getElementById("packFilter");
    const suiteFilter = document.getElementById("suiteFilter");
    const searchFilter = document.getElementById("searchFilter");
    const sortControl = document.getElementById("sortControl");
    const highlights = document.getElementById("highlights");
    const leaderRows = document.getElementById("leaderRows");
    const state = {{
      role: "all",
      pack: "all",
      suite: "all",
      search: "",
      sort: "lift_desc",
    }};

    function pct(value) {{
      if (typeof value !== "number") return "";
      return (value * 100).toFixed(2) + "%";
    }}

    function pctSigned(value) {{
      if (typeof value !== "number") return "";
      const sign = value >= 0 ? "+" : "-";
      return sign + (Math.abs(value) * 100).toFixed(2) + "%";
    }}

    function ciTip(label, meanValue, lowValue, highValue) {{
      const meanNum = Number(meanValue);
      const lowNum = Number(lowValue);
      const highNum = Number(highValue);
      if (!Number.isFinite(meanNum) || !Number.isFinite(lowNum) || !Number.isFinite(highNum)) {{
        return `${{label}} mean`;
      }}
      const half = Math.abs(highNum - lowNum) / 2;
      return `${{label}} mean ${{pct(meanNum)}}; ±${{(half * 100).toFixed(2)}}pp; 95% CI [${{pct(lowNum)}}, ${{pct(highNum)}}]`;
    }}

    function normalizeSuite(value) {{
      const raw = String(value || "").trim();
      if (raw === "quick" || raw === "dev" || raw === "dev10" || raw === "dev50" || raw === "test") return raw;
      if (!raw) return "unknown";
      return "mixed";
    }}

    function officialRole(entry) {{
      if (!entry.official_submission) return "community";
      const token = normalizeSuite(entry.suite);
      if (token === "dev" || token === "dev50" || token === "test") return "headline";
      if (token === "dev10" || token === "quick") return "sanity";
      return "other";
    }}

    function roleBadge(role) {{
      if (role === "headline") return "<span class='badge badge-headline'>headline</span>";
      if (role === "sanity") return "<span class='badge badge-sanity'>sanity</span>";
      if (role === "community") return "<span class='badge badge-community'>community</span>";
      return "<span class='badge badge-other'>other</span>";
    }}

    function reliability(entry) {{
      return Number(entry.total_model_call_errors || 0) + Number(entry.total_model_call_timeouts || 0);
    }}

    function shortId(value, limit) {{
      const text = String(value || "");
      if (text.length <= limit) return text;
      return text.slice(0, Math.max(1, limit - 1)) + "…";
    }}

    function shortCommit(value) {{
      const text = String(value || "");
      return text ? text.slice(0, 8) : "-";
    }}

    function compareNumbersDesc(left, right, picker) {{
      const a = Number(picker(left) || 0);
      const b = Number(picker(right) || 0);
      if (b !== a) return b - a;
      return String(right.generated_at || "").localeCompare(String(left.generated_at || ""));
    }}

    function compareReliabilityAsc(left, right) {{
      const a = reliability(left);
      const b = reliability(right);
      if (a !== b) return a - b;
      const mentoredA = Number((left.best_worker || {{}}).mentored_pass_rate || 0);
      const mentoredB = Number((right.best_worker || {{}}).mentored_pass_rate || 0);
      if (mentoredB !== mentoredA) return mentoredB - mentoredA;
      return String(right.generated_at || "").localeCompare(String(left.generated_at || ""));
    }}

    function sortRows(rows) {{
      const sorted = rows.slice();
      if (state.sort === "baseline_desc") {{
        sorted.sort((a, b) => compareNumbersDesc(a, b, (row) => (row.best_worker || {{}}).baseline_pass_rate));
        return sorted;
      }}
      if (state.sort === "mentored_desc") {{
        sorted.sort((a, b) => compareNumbersDesc(a, b, (row) => (row.best_worker || {{}}).mentored_pass_rate));
        return sorted;
      }}
      if (state.sort === "reliability_asc") {{
        sorted.sort(compareReliabilityAsc);
        return sorted;
      }}
      sorted.sort((a, b) => compareNumbersDesc(a, b, (row) => (row.best_worker || {{}}).lift));
      return sorted;
    }}

    function matchesSearch(entry) {{
      if (!state.search) return true;
      const worker = entry.best_worker || {{}};
      const haystack = [
        entry.submission_id,
        entry.task_pack,
        entry.suite,
        entry.git_commit_hash,
        worker.worker_model,
        entry.submission_label,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(state.search);
    }}

    function rowMatches(entry) {{
      const role = officialRole(entry);
      const roleOk = state.role === "all" || role === state.role;
      const packOk = state.pack === "all" || entry.task_pack === state.pack;
      const suiteToken = normalizeSuite(entry.suite);
      const suiteOk = state.suite === "all" || suiteToken === state.suite;
      return roleOk && packOk && suiteOk && matchesSearch(entry);
    }}

    function pickBest(rows, scorer, tiebreaker) {{
      if (rows.length === 0) return null;
      return rows.slice().sort((a, b) => {{
        const sa = scorer(a);
        const sb = scorer(b);
        if (sa !== sb) return sb - sa;
        return tiebreaker(a, b);
      }})[0];
    }}

    function renderHighlights(rows) {{
      highlights.innerHTML = "";
      if (rows.length === 0) {{
        const empty = document.createElement("div");
        empty.className = "hl-card";
        empty.innerHTML = "<div class='hl-label'>No rows</div><div class='hl-worker'>No matching submissions for current filters.</div>";
        highlights.appendChild(empty);
        return;
      }}

      if (rows.length < 2) {{
        const cards = [
          "Best baseline",
          "Best lift",
          "Most reliable",
        ];
        for (const label of cards) {{
          const tile = document.createElement("article");
          tile.className = "hl-card";
          tile.innerHTML = `
            <div class="hl-label">${{label}}</div>
            <div class="hl-worker">n/a</div>
            <div class="hl-value">n/a</div>
            <div class="hl-sub">Need 2+ filtered rows</div>
          `;
          highlights.appendChild(tile);
        }}
        return;
      }}

      const bestBaseline = pickBest(
        rows,
        (row) => Number((row.best_worker || {{}}).baseline_pass_rate || 0),
        (a, b) => String(b.generated_at || "").localeCompare(String(a.generated_at || "")),
      );
      const bestLift = pickBest(
        rows,
        (row) => Number((row.best_worker || {{}}).lift || 0),
        (a, b) => String(b.generated_at || "").localeCompare(String(a.generated_at || "")),
      );
      const bestReliability = rows.slice().sort(compareReliabilityAsc)[0];

      const cards = [
        {{
          label: "Best baseline",
          row: bestBaseline,
          value: pct(Number((bestBaseline.best_worker || {{}}).baseline_pass_rate || 0)),
        }},
        {{
          label: "Best lift",
          row: bestLift,
          value: pctSigned(Number((bestLift.best_worker || {{}}).lift || 0)),
        }},
        {{
          label: "Most reliable",
          row: bestReliability,
          value: `${{reliability(bestReliability)}} model-call issues (errors+timeouts)`,
        }},
      ];

      for (const card of cards) {{
        const row = card.row;
        const worker = row.best_worker || {{}};
        const tile = document.createElement("article");
        tile.className = "hl-card";
        tile.innerHTML = `
          <div class="hl-label">${{card.label}}</div>
          <div class="hl-worker" title="${{worker.worker_model || ""}}">${{worker.worker_model || "-"}}</div>
          <div class="hl-value">${{card.value}}</div>
          <div class="hl-sub" title="${{row.submission_id || ""}}">${{shortId(row.submission_id || "-", 24)}}</div>
        `;
        highlights.appendChild(tile);
      }}
    }}

    function render() {{
      const filtered = entries.filter(rowMatches);
      const sorted = sortRows(filtered);

      renderHighlights(sorted);

      leaderRows.innerHTML = "";
      if (sorted.length === 0) {{
        leaderRows.innerHTML = "<tr><td colspan='11'>No submissions match current filters.</td></tr>";
        return;
      }}

      for (const entry of sorted) {{
        const worker = entry.best_worker || {{}};
        const role = officialRole(entry);
        const commit = String(entry.git_commit_hash || "");
        const baselineTip = ciTip("Baseline", entry.baseline_mean, entry.baseline_ci_low, entry.baseline_ci_high);
        const mentoredTip = ciTip("Mentored", entry.mentored_mean, entry.mentored_ci_low, entry.mentored_ci_high);
        const liftTip = ciTip("Lift", entry.lift_mean, entry.lift_ci_low, entry.lift_ci_high);
        const sigMarker = entry.lift_significant
          ? "<span class='sig-marker' title='Lift CI excludes 0 (significant)'>sig</span>"
          : "";
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><span class="text-clip" title="${{entry.submission_id || ""}}">${{entry.submission_id || "-"}}</span></td>
          <td>${{roleBadge(role)}}</td>
          <td><span class="text-clip" title="${{entry.task_pack || ""}}">${{entry.task_pack || "-"}}</span></td>
          <td><span class="text-clip" title="${{normalizeSuite(entry.suite)}}">${{normalizeSuite(entry.suite)}}</span></td>
          <td><span class="text-clip" title="${{worker.worker_model || ""}}">${{worker.worker_model || "-"}}</span></td>
          <td class="num"><span class="metric" title="${{baselineTip}}">${{pct(Number(worker.baseline_pass_rate || 0))}}</span></td>
          <td class="num"><span class="metric" title="${{mentoredTip}}">${{pct(Number(worker.mentored_pass_rate || 0))}}</span></td>
          <td class="num"><span class="metric" title="${{liftTip}}">${{pctSigned(Number(worker.lift || 0))}}</span>${{sigMarker}}</td>
          <td class="num">${{Number(entry.total_model_call_errors || 0)}}</td>
          <td class="num">${{Number(entry.total_model_call_timeouts || 0)}}</td>
          <td>
            <span class="commit-wrap">
              <span class="text-clip" title="${{commit || "-"}}">${{shortCommit(commit)}}</span>
              <button class="copy-btn" type="button" data-commit="${{commit}}">Copy</button>
            </span>
          </td>
        `;
        leaderRows.appendChild(tr);
      }}
    }}

    function defaultSuiteToken() {{
      const suites = new Set(entries.map((entry) => normalizeSuite(entry.suite)));
      if (suites.has("dev50")) {{
        return "dev50";
      }}
      if (suites.has("quick")) {{
        return "quick";
      }}
      return "all";
    }}

    function setDefaults() {{
      const packHasV2 = entries.some((entry) => entry.task_pack === "task_pack_v2");
      state.pack = packHasV2 ? "task_pack_v2" : "all";
      state.suite = "all";

      packFilter.value = state.pack;
      suiteFilter.value = state.suite;
      sortControl.value = state.sort;
      searchFilter.value = "";
    }}

    function bindEvents() {{
      tabs.forEach((tab) => {{
        tab.addEventListener("click", () => {{
          const role = String(tab.dataset.role || "all");
          state.role = role;
          if (role === "all") {{
            state.suite = "all";
            suiteFilter.value = "all";
          }} else if (state.suite === "all") {{
            state.suite = defaultSuiteToken();
            suiteFilter.value = state.suite;
          }}
          tabs.forEach((item) => item.classList.toggle("active", item === tab));
          render();
        }});
      }});

      packFilter.addEventListener("change", () => {{
        state.pack = packFilter.value;
        render();
      }});

      suiteFilter.addEventListener("change", () => {{
        state.suite = suiteFilter.value;
        render();
      }});

      sortControl.addEventListener("change", () => {{
        state.sort = sortControl.value;
        render();
      }});

      searchFilter.addEventListener("input", () => {{
        state.search = String(searchFilter.value || "").trim().toLowerCase();
        render();
      }});

      leaderRows.addEventListener("click", async (event) => {{
        const target = event.target;
        if (!(target instanceof HTMLElement)) return;
        if (!target.classList.contains("copy-btn")) return;
        const commit = String(target.dataset.commit || "");
        if (!commit || commit === "-") return;
        const original = target.textContent || "Copy";
        try {{
          if (navigator.clipboard && navigator.clipboard.writeText) {{
            await navigator.clipboard.writeText(commit);
          }} else {{
            const temp = document.createElement("textarea");
            temp.value = commit;
            document.body.appendChild(temp);
            temp.select();
            document.execCommand("copy");
            document.body.removeChild(temp);
          }}
          target.textContent = "Copied";
        }} catch (error) {{
          target.textContent = "Failed";
        }}
        window.setTimeout(() => {{
          target.textContent = original;
        }}, 1000);
      }});
    }}

    setDefaults();
    bindEvents();
    render();
  </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify submissions and regenerate community leaderboard artifacts.")
    parser.add_argument(
        "--submissions-dir",
        default="submissions",
        help="Root directory scanned recursively for tracked submission bundles.",
    )
    parser.add_argument("--leaderboard-dir", default="leaderboard")
    parser.add_argument("--docs-html", default="docs/index.html")
    parser.add_argument("--docs-markdown", default="docs/leaderboard.md")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any submission in submissions-dir does not verify.",
    )
    args = parser.parse_args()

    submissions_dir = Path(args.submissions_dir)
    leaderboard_dir = Path(args.leaderboard_dir)
    docs_html = Path(args.docs_html)
    docs_markdown = Path(args.docs_markdown)

    submissions_dir.mkdir(parents=True, exist_ok=True)
    leaderboard_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir = leaderboard_dir / "submissions"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    zip_paths = _submission_zip_paths(submissions_dir)
    valid_entries: list[dict[str, Any]] = []
    failed_reports: list[dict[str, Any]] = []

    for path in zip_paths:
        report = verify_submission_bundle(path)
        if not report.get("ok"):
            failed_reports.append({"submission": path.name, "errors": report.get("errors", [])})
            continue
        valid_entries.append(_normalize_submission(path))

    # Remove stale normalized payloads before rewriting.
    for existing in normalized_dir.glob("*.json"):
        existing.unlink()
    for entry in valid_entries:
        out = normalized_dir / f"{entry['submission_id']}.json"
        out.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    generated_at = max((str(row.get("generated_at", "")) for row in valid_entries), default="n/a")
    headline_official_runs = _headline_official_runs(valid_entries)
    official_sanity_runs = _sanity_official_runs(valid_entries)
    summary = {
        "generated_at": generated_at,
        "submission_count": len(valid_entries),
        "official_count": sum(1 for row in valid_entries if row.get("official_submission")),
        "community_count": sum(1 for row in valid_entries if not row.get("official_submission")),
        "failed_count": len(failed_reports),
        "failed_submissions": failed_reports,
        "official_policy": {
            "headline_suites": sorted(HEADLINE_SUITES),
            "sanity_suites": sorted(SANITY_SUITES),
            "headline_description": "Headline official baselines come from dev/dev50/test suites.",
            "sanity_description": "Official dev10/quick runs are sanity checks for harness health.",
        },
        "entries": sorted(valid_entries, key=_sort_key, reverse=True),
        "headline_official_runs": headline_official_runs,
        "official_sanity_runs": official_sanity_runs,
        # Backward-compatible alias retained for existing consumers.
        "latest_official_runs": headline_official_runs,
    }

    (leaderboard_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_markdown(summary["entries"], docs_markdown, generated_at=generated_at)
    _render_index_html(summary, docs_html)
    (docs_html.parent / ".nojekyll").write_text("", encoding="utf-8")
    (normalized_dir / ".gitkeep").write_text("", encoding="utf-8")

    print(f"Verified submissions: {len(valid_entries)}")
    print(f"Failed submissions: {len(failed_reports)}")
    print(f"Wrote summary: {leaderboard_dir / 'summary.json'}")
    print(f"Wrote docs HTML: {docs_html}")
    print(f"Wrote docs markdown: {docs_markdown}")

    if args.strict and failed_reports:
        for item in failed_reports:
            print(f"FAILED {item['submission']}:")
            for error in item["errors"]:
                print(f"- {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
