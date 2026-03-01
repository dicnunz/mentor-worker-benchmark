# Task: Marker Extraction (medium)

Fix `extract_markers` in `src/solution.py`.

A marker is `@` followed by one or more characters from `[A-Za-z0-9_]`.

Requirements:
- Normalize tokens to lowercase.
- Ignore tokens shorter than `MIN_LEN` (2).
- Ignore tokens when the marker is embedded inside an identifier (the previous character is alphanumeric or underscore).
- Deduplicate while preserving first-seen order.
- Keep the function signature unchanged.

Example:
- Input: `... @Alpha_1 ... @alpha_1 ...`
- Output: `["alpha_1"]`

## Quality Gate Expectations
Implement all behavior required by tests, including edge-case handling and deterministic output.

## Input/Output Examples
- Example 1 input/output contract: `assert extract_markers(text) == ['cinder_0', 'quartz2']`
- Example 2 input/output contract: `assert extract_markers(text) == ['feather5']`

## Required Edge Cases
- Handle empty input gracefully.
- Preserve deterministic ordering when deduplicating.
- Reject invalid inputs where required by the tests.
