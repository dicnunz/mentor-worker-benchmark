# Task: Refactor `parse_query_string`

Refactor `parse_query_string(query: str)` in `src/solution.py`.

Requirements:
- URL-decode keys/values (including `+` as space).
- Support repeated keys by storing a list of values.
- Keep single-occurrence keys as strings.
- Ignore empty segments.
