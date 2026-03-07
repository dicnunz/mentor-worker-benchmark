#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    return "n/a"


def _signed_pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        sign = "+" if value >= 0 else "-"
        return f"{sign}{abs(value) * 100:.2f}%"
    return "n/a"


def _suite_rank(value: str) -> int:
    ranks = {
        "dev": 0,
        "dev50": 1,
        "test": 2,
        "dev10": 3,
        "quick": 4,
        "mixed": 5,
        "unknown": 6,
    }
    return ranks.get(value, 6)


def _top_baseline(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    return max(
        entries,
        key=lambda row: (
            float(row.get("baseline_mean", 0.0) or 0.0),
            float(row.get("mentored_mean", 0.0) or 0.0),
            -_suite_rank(str(row.get("suite", ""))),
            int(bool(row.get("official_submission"))),
        ),
    )


def _best_lift(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    return max(
        entries,
        key=lambda row: (
            float(row.get("lift_mean", 0.0) or 0.0),
            int(bool(row.get("lift_significant"))),
            -int(row.get("total_model_call_errors", 0) or 0),
            -int(row.get("total_model_call_timeouts", 0) or 0),
        ),
    )


def _most_reliable(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    return min(
        entries,
        key=lambda row: (
            int(row.get("total_model_call_errors", 0) or 0),
            int(row.get("total_model_call_timeouts", 0) or 0),
            -int(row.get("total_runs", 0) or 0),
            -int(bool(row.get("official_submission"))),
            _suite_rank(str(row.get("suite", ""))),
            str(row.get("submission_id", "")),
        ),
    )


def _headline_baseline(summary: dict[str, Any]) -> dict[str, Any] | None:
    rows = summary.get("headline_official_runs")
    if not isinstance(rows, list) or not rows:
        return None
    return rows[0] if isinstance(rows[0], dict) else None


def _worker_name(entry: dict[str, Any]) -> str:
    worker = entry.get("best_worker", {})
    if isinstance(worker, dict):
        return str(worker.get("worker_model", "")) or "unknown"
    return "unknown"


def _mentor_name(entry: dict[str, Any]) -> str:
    mentor = entry.get("best_mentor", {})
    if isinstance(mentor, dict):
        return str(mentor.get("mentor_model", "")) or "unknown"
    return "unknown"


def _line_for_top_baseline(entry: dict[str, Any]) -> str:
    return (
        f"- Top baseline: `{_pct(entry.get('baseline_mean'))}` from `{entry.get('submission_id')}` "
        f"({entry.get('suite')}, worker `{_worker_name(entry)}`, "
        f"errors `{entry.get('total_model_call_errors', 0)}`, "
        f"timeouts `{entry.get('total_model_call_timeouts', 0)}`)."
    )


def _line_for_best_lift(entry: dict[str, Any]) -> str:
    return (
        f"- Best mentor lift: `{_signed_pct(entry.get('lift_mean'))}` from `{entry.get('submission_id')}` "
        f"({entry.get('suite')}, worker `{_worker_name(entry)}`, mentor `{_mentor_name(entry)}`, "
        f"baseline `{_pct(entry.get('baseline_mean'))}`, mentored `{_pct(entry.get('mentored_mean'))}`)."
    )


def _line_for_reliable(entry: dict[str, Any]) -> str:
    return (
        f"- Most reliable run: `{entry.get('submission_id')}` "
        f"({entry.get('suite')}, `{entry.get('total_runs', 0)}` total runs, "
        f"errors `{entry.get('total_model_call_errors', 0)}`, "
        f"timeouts `{entry.get('total_model_call_timeouts', 0)}`, "
        f"worker `{_worker_name(entry)}`)."
    )


def build_summary(summary: dict[str, Any]) -> str:
    entries = summary.get("entries")
    if not isinstance(entries, list):
        entries = []
    entries = [row for row in entries if isinstance(row, dict)]

    top_baseline = _top_baseline(entries)
    best_lift = _best_lift(entries)
    most_reliable = _most_reliable(entries)
    headline = _headline_baseline(summary)

    lines = [
        "# Post-Ready Benchmark Snapshot",
        "",
        f"Generated from `leaderboard/summary.json`: `{summary.get('generated_at', 'unknown')}`",
        "",
        f"Verified submissions: `{summary.get('submission_count', 0)}` total "
        f"(`{summary.get('official_count', 0)}` official, `{summary.get('community_count', 0)}` community).",
        "",
        "## What This Measures",
        "",
        "- `mentor-worker-benchmark` measures whether a mentor model improves a worker model on deterministic local Python repair tasks scored by bundled `pytest` tests.",
        "- The key outputs are worker-only baseline pass rate, mentored pass rate, paired lift, and model-call reliability (errors/timeouts).",
        "",
        "## Current Snapshot",
        "",
    ]

    if top_baseline is not None:
        lines.append(_line_for_top_baseline(top_baseline))
    if best_lift is not None:
        lines.append(_line_for_best_lift(best_lift))
    if most_reliable is not None:
        lines.append(_line_for_reliable(most_reliable))

    if headline is not None:
        lines.extend(
            [
                "",
                "## Headline Official Baseline",
                "",
                f"- Current headline official row: `{headline.get('submission_id')}` "
                f"({headline.get('suite')}, baseline `{_pct(headline.get('baseline_mean'))}`, "
                f"mentored `{_pct(headline.get('mentored_mean'))}`, lift `{_signed_pct(headline.get('lift_mean'))}`).",
            ]
        )

    lines.extend(
        [
            "",
            "## Honest Limitation",
            "",
            "- Local `quick` and `dev10` health verification is useful for checking benchmark behavior and low-error execution on this machine, but it is not the same thing as a full headline publication run on `dev`, `dev50`, or `test`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a compact post-ready summary from leaderboard/summary.json.")
    parser.add_argument("--summary", default="leaderboard/summary.json")
    parser.add_argument("--out", default="docs/post_ready_summary.md")
    args = parser.parse_args()

    summary_path = Path(args.summary)
    output_path = Path(args.out)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_summary(summary) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
