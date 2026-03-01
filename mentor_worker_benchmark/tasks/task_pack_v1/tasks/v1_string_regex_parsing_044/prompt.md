# Task: Marker Extraction (hard)

Fix `extract_markers` in `src/solution.py`.

A marker is `&` followed by one or more characters from `[A-Za-z0-9_]`.

Requirements:
- Normalize tokens to lowercase.
- Ignore tokens shorter than `MIN_LEN` (4).
- Ignore tokens when the marker is embedded inside an identifier (the previous character is alphanumeric or underscore).
- Deduplicate while preserving first-seen order.
- Keep the function signature unchanged.

Example:
- Input: `... &Alpha_1 ... &alpha_1 ...`
- Output: `["alpha_1"]`
