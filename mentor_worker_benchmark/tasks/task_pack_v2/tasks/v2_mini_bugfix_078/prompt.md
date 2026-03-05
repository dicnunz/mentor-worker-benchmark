# Mini-Repo Bugfix (medium)

Fix the integration behavior across modules for `build_report` in `src/pipeline.py`.

Input rows are delimited by `|` and should flow through:
- `src/loader.py` -> parse valid rows
- `src/metrics.py` -> aggregate summary metrics
- `src/pipeline.py` -> orchestrate end-to-end report

Requirements:
- Ignore malformed rows.
- Count `above_threshold` with strict `>` comparison.
- `top_label` should be the label with highest score (tie -> lexical).
- Keep signatures unchanged.

Example input:
- `grove|7|core`
- `signal|9|edge`
