#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.runner import write_leaderboard


def _table_html(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    header = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body_rows: list[str] = []

    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(key, '')))}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{cells}</tr>")

    body = "\n".join(body_rows) if body_rows else "<tr><td colspan='99'>No data</td></tr>"
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def _pct(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2%}"
    return str(value)


def render_docs_html(results: dict[str, Any], output_path: Path) -> None:
    aggregates = results.get("aggregates", {})

    mentors = [
        {
            "mentor_model": row.get("mentor_model", ""),
            "avg_lift_across_workers": _pct(row.get("avg_lift_across_workers", 0.0)),
            "overall_mentored_pass_rate": _pct(row.get("overall_mentored_pass_rate", 0.0)),
            "mentor_violation_rate": _pct(row.get("mentor_violation_rate", 0.0)),
        }
        for row in aggregates.get("best_mentors", [])
    ]

    workers = [
        {
            "worker_model": row.get("worker_model", ""),
            "baseline_pass_rate": _pct(row.get("baseline_pass_rate", 0.0)),
            "mentored_pass_rate": _pct(row.get("mentored_pass_rate", 0.0)),
            "control_pass_rate": _pct(row.get("control_pass_rate", 0.0)),
            "delta": _pct(row.get("delta", 0.0)),
        }
        for row in aggregates.get("best_workers", [])
    ]

    categories = [
        {
            "category": row.get("category", ""),
            "baseline_pass_rate": _pct(row.get("baseline_pass_rate", 0.0)),
            "mentored_pass_rate": _pct(row.get("mentored_pass_rate", 0.0)),
            "control_pass_rate": _pct(row.get("control_pass_rate", 0.0)),
            "mentorship_lift": _pct(row.get("mentorship_lift", 0.0)),
        }
        for row in aggregates.get("category_breakdown", [])
    ]

    mentors_table = _table_html(
        mentors,
        [
            ("mentor_model", "Mentor"),
            ("avg_lift_across_workers", "Avg Lift"),
            ("overall_mentored_pass_rate", "Mentored Pass Rate"),
            ("mentor_violation_rate", "Violation Rate"),
        ],
    )

    workers_table = _table_html(
        workers,
        [
            ("worker_model", "Worker"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("control_pass_rate", "Control"),
            ("delta", "Lift"),
        ],
    )

    categories_table = _table_html(
        categories,
        [
            ("category", "Category"),
            ("baseline_pass_rate", "Baseline"),
            ("mentored_pass_rate", "Mentored"),
            ("control_pass_rate", "Control"),
            ("mentorship_lift", "Lift"),
        ],
    )

    generated = str(results.get("generated_at", "unknown"))
    summary = results.get("summary", {})
    total_runs = summary.get("total_runs", 0)
    wall = summary.get("benchmark_wall_time_seconds", 0)

    page = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Mentor Worker Benchmark Leaderboard</title>
  <style>
    :root {{
      --bg: #f7f8fa;
      --card: #ffffff;
      --text: #1f2430;
      --muted: #5c667a;
      --line: #dde3ee;
      --accent: #0f5cc0;
    }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: radial-gradient(circle at 0% 0%, #e9eef8 0, var(--bg) 45%);
      color: var(--text);
    }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      padding: 2rem 1rem 3rem;
    }}
    h1 {{ margin: 0 0 0.5rem; font-size: 1.9rem; }}
    .meta {{ color: var(--muted); margin-bottom: 1.5rem; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 1rem;
      margin: 0 0 1rem;
      overflow-x: auto;
      box-shadow: 0 3px 12px rgba(15, 34, 68, 0.06);
    }}
    table {{ border-collapse: collapse; width: 100%; min-width: 600px; }}
    th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 0.55rem; font-size: 0.92rem; }}
    th {{ color: var(--muted); font-weight: 600; }}
    td {{ color: var(--text); }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main>
    <h1>Mentor Worker Benchmark</h1>
    <div class=\"meta\">Generated: {html.escape(generated)} | Runs: {total_runs} | Wall time: {wall}s</div>

    <section class=\"card\">
      <h2>Best Mentors</h2>
      {mentors_table}
    </section>

    <section class=\"card\">
      <h2>Best Workers</h2>
      {workers_table}
    </section>

    <section class=\"card\">
      <h2>Per-Category Breakdown</h2>
      {categories_table}
    </section>

    <p class=\"meta\">Generated from <code>results/results.json</code>. Markdown version: <a href=\"../results/leaderboard.md\">results/leaderboard.md</a></p>
  </main>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish leaderboard markdown + docs HTML from results JSON.")
    parser.add_argument("--results", default="results/results.json")
    parser.add_argument("--markdown-out", default="results/leaderboard.md")
    parser.add_argument("--html-out", default="docs/single_run.html")
    args = parser.parse_args()

    results_path = Path(args.results)
    if not results_path.exists():
        raise SystemExit(f"Results file not found: {results_path}")

    payload = json.loads(results_path.read_text(encoding="utf-8"))

    markdown_path = Path(args.markdown_out)
    write_leaderboard(payload, markdown_path)

    html_path = Path(args.html_out)
    render_docs_html(payload, html_path)

    nojekyll_path = html_path.parent / ".nojekyll"
    nojekyll_path.write_text("", encoding="utf-8")

    print(f"Wrote markdown leaderboard: {markdown_path}")
    print(f"Wrote docs page: {html_path}")


if __name__ == "__main__":
    main()
