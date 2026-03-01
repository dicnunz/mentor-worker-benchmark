# Task: Mini Module Pipeline (hard)

This task spans multiple files under `src/`.

Fix the mini-module so `summarize(raw: str)` in `src/pipeline.py` returns a stable report.

Rules:
- Use separator `->`.
- Ignore malformed lines and non-integer values.
- Normalize keys to lowercase.
- Aggregate duplicate keys by summing values.
- Return report with keys:
  - `total`
  - `unique_keys`
  - `top_key` (highest value, tie -> lexicographically smallest key)
  - `top_value`
