# Task: Trimmed Mean (easy)

Fix `trimmed_mean(values, trim_ratio)` in `src/solution.py`.

Requirements:
- `trim_ratio` must satisfy `0 <= trim_ratio < 0.5`, else raise `ValueError`.
- Ignore `NaN` values.
- Sort remaining values.
- Trim `int(n * trim_ratio)` values from each end.
- Raise `ValueError` if no values remain.
- Return the arithmetic mean of the retained values.
