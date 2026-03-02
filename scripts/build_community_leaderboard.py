#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    derived_metrics, metrics_source = _derive_metrics(
        summary=summary if isinstance(summary, dict) else {},
        config=config if isinstance(config, dict) else {},
        runs=runs,
    )

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
        "best_worker": {
            "worker_model": str(best_worker.get("worker_model", "")) if isinstance(best_worker, dict) else "",
            "baseline_pass_rate": round(
                _safe_float(best_worker.get("baseline_pass_rate", 0.0)) if isinstance(best_worker, dict) else 0.0,
                4,
            ),
            "mentored_pass_rate": round(
                _safe_float(best_worker.get("mentored_pass_rate", 0.0)) if isinstance(best_worker, dict) else 0.0,
                4,
            ),
            "control_pass_rate": round(
                _safe_float(best_worker.get("control_pass_rate", 0.0)) if isinstance(best_worker, dict) else 0.0,
                4,
            ),
            "lift": round(_safe_float(best_worker.get("delta", 0.0)) if isinstance(best_worker, dict) else 0.0, 4),
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
    entries_json = json.dumps(summary.get("entries", []))
    generated_at = html.escape(str(summary.get("generated_at", "")))
    official_count = int(summary.get("official_count", 0))
    community_count = int(summary.get("community_count", 0))
    total_count = int(summary.get("submission_count", 0))

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mentor Worker Benchmark Community Leaderboard</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --card: #ffffff;
      --text: #1d2433;
      --muted: #5b6782;
      --line: #dbe2ef;
      --accent: #0f5cc0;
      --warn: #b45309;
      --ok: #0f766e;
    }}
    body {{
      margin: 0;
      font-family: "SF Pro Text", "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 0% 0%, #e7eefb 0, var(--bg) 46%);
      color: var(--text);
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 1.6rem 1rem 2.4rem;
    }}
    h1 {{ margin: 0; font-size: 2rem; }}
    .meta {{
      color: var(--muted);
      margin-top: 0.45rem;
      margin-bottom: 1.2rem;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 1rem;
      box-shadow: 0 3px 12px rgba(15, 34, 68, 0.06);
      overflow-x: auto;
    }}
    .controls {{
      display: flex;
      gap: 0.8rem;
      flex-wrap: wrap;
      align-items: center;
    }}
    label {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    select {{
      padding: 0.35rem 0.55rem;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: #fff;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      min-width: 760px;
    }}
    th, td {{
      text-align: left;
      border-bottom: 1px solid var(--line);
      padding: 0.5rem;
      font-size: 0.92rem;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .badge {{
      display: inline-block;
      padding: 0.18rem 0.5rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 600;
      border: 1px solid transparent;
    }}
    .badge-official {{
      color: var(--ok);
      border-color: #99f6e4;
      background: #f0fdfa;
    }}
    .badge-community {{
      color: var(--warn);
      border-color: #fde68a;
      background: #fffbeb;
    }}
    .small {{
      color: var(--muted);
      font-size: 0.85rem;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main>
    <h1>Mentor Worker Benchmark Community Leaderboard</h1>
    <p class="meta">
      Generated: {generated_at} |
      Submissions: {total_count} |
      Official: {official_count} |
      Community: {community_count}
    </p>

    <section class="card">
      <h2>Filters</h2>
      <div class="controls">
        <label for="packFilter">Task Pack</label>
        <select id="packFilter">
          <option value="all">all</option>
          <option value="task_pack_v1">task_pack_v1</option>
          <option value="task_pack_v2">task_pack_v2</option>
        </select>
        <label for="suiteFilter">Suite</label>
        <select id="suiteFilter">
          <option value="all">all</option>
          <option value="quick">quick</option>
          <option value="dev10">dev10</option>
          <option value="dev">dev</option>
          <option value="dev50">dev50</option>
          <option value="test">test</option>
          <option value="mixed">mixed</option>
        </select>
      </div>
      <p class="small">Headline policy: official `dev`/`dev50`/`test` runs are baseline headline numbers. Official `dev10`/`quick` runs are sanity-only harness checks.</p>
    </section>

    <section class="card">
      <h2>Headline Official Baselines</h2>
      <table>
        <thead>
          <tr>
            <th>Submission</th>
            <th>Pack</th>
            <th>Suite</th>
            <th>Top Worker</th>
            <th>Baseline</th>
            <th>Mentored</th>
            <th>Lift</th>
            <th>Commit</th>
          </tr>
        </thead>
        <tbody id="officialRows"></tbody>
      </table>
    </section>

    <section class="card">
      <h2>Official Sanity Runs</h2>
      <table>
        <thead>
          <tr>
            <th>Submission</th>
            <th>Pack</th>
            <th>Suite</th>
            <th>Top Worker</th>
            <th>Baseline</th>
            <th>Mentored</th>
            <th>Model Errors</th>
            <th>Timeouts</th>
            <th>Commit</th>
          </tr>
        </thead>
        <tbody id="sanityRows"></tbody>
      </table>
    </section>

    <section class="card">
      <h2>All Verified Submissions</h2>
      <table>
        <thead>
          <tr>
            <th>Submission</th>
            <th>Label</th>
            <th>Role</th>
            <th>Pack</th>
            <th>Suite</th>
            <th>Top Worker</th>
            <th>Baseline</th>
            <th>Mentored</th>
            <th>Lift</th>
            <th>Model Errors</th>
            <th>Timeouts</th>
            <th>Commit</th>
          </tr>
        </thead>
        <tbody id="submissionRows"></tbody>
      </table>
    </section>

    <p class="meta">Raw normalized summaries: <a href="../leaderboard/summary.json">leaderboard/summary.json</a> | Markdown: <a href="./leaderboard.md">docs/leaderboard.md</a></p>
  </main>
  <script>
    const entries = {entries_json};
    const packFilter = document.getElementById("packFilter");
    const suiteFilter = document.getElementById("suiteFilter");
    const officialRows = document.getElementById("officialRows");
    const sanityRows = document.getElementById("sanityRows");
    const submissionRows = document.getElementById("submissionRows");

    function pct(value) {{
      if (typeof value !== "number") return "";
      return (value * 100).toFixed(2) + "%";
    }}

    function normalizeSuite(value) {{
      const raw = String(value || "").trim();
      if (raw === "quick" || raw === "dev" || raw === "dev10" || raw === "dev50" || raw === "test") return raw;
      if (!raw) return "unknown";
      return "mixed";
    }}

    function suitePriority(value) {{
      const token = normalizeSuite(value);
      if (token === "dev") return 0;
      if (token === "dev50") return 1;
      if (token === "test") return 2;
      if (token === "dev10") return 3;
      if (token === "quick") return 4;
      if (token === "mixed") return 5;
      return 6;
    }}

    function officialRole(entry) {{
      if (!entry.official_submission) return "community";
      const token = normalizeSuite(entry.suite);
      if (token === "dev" || token === "dev50" || token === "test") return "headline";
      if (token === "dev10" || token === "quick") return "sanity";
      return "other";
    }}

    function rowMatches(entry) {{
      const packOk = packFilter.value === "all" || entry.task_pack === packFilter.value;
      const suiteToken = normalizeSuite(entry.suite);
      const suiteOk = suiteFilter.value === "all" || suiteToken === suiteFilter.value;
      return packOk && suiteOk;
    }}

    function headlineOfficial(filtered) {{
      const byPack = new Map();
      for (const entry of filtered) {{
        if (officialRole(entry) !== "headline") continue;
        const key = String(entry.task_pack || "unknown");
        if (!byPack.has(key)) {{
          byPack.set(key, []);
        }}
        byPack.get(key).push(entry);
      }}

      const selected = [];
      for (const rows of byPack.values()) {{
        rows.sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)));
        let best = rows[0];
        for (const row of rows) {{
          if (suitePriority(row.suite) < suitePriority(best.suite)) {{
            best = row;
          }}
        }}
        selected.push(best);
      }}

      selected.sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)));
      selected.sort((a, b) => suitePriority(a.suite) - suitePriority(b.suite));
      return selected;
    }}

    function sanityOfficial(filtered) {{
      const rows = filtered.filter((entry) => officialRole(entry) === "sanity");
      rows.sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)));
      rows.sort((a, b) => suitePriority(a.suite) - suitePriority(b.suite));
      return rows;
    }}

    function render() {{
      const filtered = entries.filter(rowMatches).sort((a, b) => String(b.generated_at).localeCompare(String(a.generated_at)));
      const official = headlineOfficial(filtered);
      const sanity = sanityOfficial(filtered);

      officialRows.innerHTML = "";
      if (official.length === 0) {{
        officialRows.innerHTML = "<tr><td colspan='8'>No headline official runs for current filters.</td></tr>";
      }} else {{
        for (const entry of official) {{
          const worker = entry.best_worker || {{}};
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${{entry.submission_id}}</td>
            <td>${{entry.task_pack}}</td>
            <td>${{normalizeSuite(entry.suite)}}</td>
            <td>${{worker.worker_model || ""}}</td>
            <td>${{pct(worker.baseline_pass_rate)}}</td>
            <td>${{pct(worker.mentored_pass_rate)}}</td>
            <td>${{pct(worker.lift)}}</td>
            <td>${{entry.git_commit_hash}}</td>
          `;
          officialRows.appendChild(tr);
        }}
      }}

      sanityRows.innerHTML = "";
      if (sanity.length === 0) {{
        sanityRows.innerHTML = "<tr><td colspan='9'>No official sanity runs for current filters.</td></tr>";
      }} else {{
        for (const entry of sanity) {{
          const worker = entry.best_worker || {{}};
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${{entry.submission_id}}</td>
            <td>${{entry.task_pack}}</td>
            <td>${{normalizeSuite(entry.suite)}}</td>
            <td>${{worker.worker_model || ""}}</td>
            <td>${{pct(worker.baseline_pass_rate)}}</td>
            <td>${{pct(worker.mentored_pass_rate)}}</td>
            <td>${{entry.total_model_call_errors ?? 0}}</td>
            <td>${{entry.total_model_call_timeouts ?? 0}}</td>
            <td>${{entry.git_commit_hash}}</td>
          `;
          sanityRows.appendChild(tr);
        }}
      }}

      submissionRows.innerHTML = "";
      if (filtered.length === 0) {{
        submissionRows.innerHTML = "<tr><td colspan='12'>No submissions for current filters.</td></tr>";
      }} else {{
        for (const entry of filtered) {{
          const worker = entry.best_worker || {{}};
          const role = officialRole(entry);
          const badge = role === "community"
            ? "<span class='badge badge-community'>community (not official)</span>"
            : "<span class='badge badge-official'>official</span>";
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${{entry.submission_id}}</td>
            <td>${{badge}}</td>
            <td>${{role}}</td>
            <td>${{entry.task_pack}}</td>
            <td>${{normalizeSuite(entry.suite)}}</td>
            <td>${{worker.worker_model || ""}}</td>
            <td>${{pct(worker.baseline_pass_rate)}}</td>
            <td>${{pct(worker.mentored_pass_rate)}}</td>
            <td>${{pct(worker.lift)}}</td>
            <td>${{entry.total_model_call_errors ?? 0}}</td>
            <td>${{entry.total_model_call_timeouts ?? 0}}</td>
            <td>${{entry.git_commit_hash}}</td>
          `;
          submissionRows.appendChild(tr);
        }}
      }}
    }}

    packFilter.addEventListener("change", render);
    suiteFilter.addEventListener("change", render);
    render();
  </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify submissions and regenerate community leaderboard artifacts.")
    parser.add_argument("--submissions-dir", default="submissions")
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

    zip_paths = sorted(
        path
        for path in submissions_dir.glob("*.zip")
        if path.is_file() and not path.name.startswith(("local_", "tmp_"))
    )
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
