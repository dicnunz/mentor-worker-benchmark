# Task: CSV -> JSON Summary (medium)

Fix `summarize_transactions(input_csv, output_json)` in `src/solution.py`.

Input CSV columns: `user,amount,category`.

Requirements:
- Trim whitespace around all fields.
- Ignore rows with empty user names.
- Ignore rows where `amount` is not an integer.
- Aggregate per user:
  - `total`: sum of amounts
  - `count`: number of valid rows
  - `categories`: sorted unique category names
- Write JSON object keyed by user (sorted lexicographically).

## Quality Gate Expectations
Implement all behavior required by tests, including edge-case handling and deterministic output.

## Input/Output Examples
- Example 1 input/output contract: `assert payload == {'dawn': {'total': 9, 'count': 1, 'categories': ['nectar']}, 'eagle': {'total': 8, 'count': 2, 'categories': ['grove', 'nectar']}, 'yankee': {'total': 10, 'count': 2, 'categories': ['dawn']}}`
- Example 2 input/output contract: `assert list(payload) == sorted(payload)`

## Required Edge Cases
- Handle empty files and malformed rows safely.
- Keep output ordering deterministic.
- Reject invalid inputs where required by the tests.
