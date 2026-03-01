# Task: Mini Module Pipeline (medium)

This task spans multiple files under `src/`.

Fix the mini-module so `summarize(raw: str)` in `src/pipeline.py` returns a stable report.

Rules:
- Use separator `:`.
- Ignore malformed lines and non-integer values.
- Normalize keys to lowercase.
- Aggregate duplicate keys by summing values.
- Return report with keys:
  - `total`
  - `unique_keys`
  - `top_key` (highest value, tie -> lexicographically smallest key)
  - `top_value`

## Quality Gate Expectations
Implement all behavior required by tests, including edge-case handling and deterministic output.

## Input/Output Examples
- Example 1 input/output contract: `assert summarize(raw) == {'total': 17, 'unique_keys': 3, 'top_key': 'solace', 'top_value': 9}`
- Example 2 input/output contract: `assert summarize("") == {`

## Required Edge Cases
- Handle empty and malformed input rows.
- Keep aggregation semantics deterministic.
- Reject invalid inputs where required by the tests.
