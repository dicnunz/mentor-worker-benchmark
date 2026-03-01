# Task: Trimmed Mean (hard)

Fix `trimmed_mean(values, trim_ratio)` in `src/solution.py`.

Requirements:
- `trim_ratio` must satisfy `0 <= trim_ratio < 0.5`, else raise `ValueError`.
- Ignore `NaN` values.
- Sort remaining values.
- Trim `int(n * trim_ratio)` values from each end.
- Raise `ValueError` if no values remain.
- Return the arithmetic mean of the retained values.

## Quality Gate Expectations
Implement all behavior required by tests, including edge-case handling and deterministic output.

## Input/Output Examples
- Example 1 input/output contract: `assert result == pytest.approx(4.9079999999999995, rel=1e-9, abs=1e-9)`
- Example 2 input/output contract: `assert result == pytest.approx(_oracle(values, 0.25), rel=1e-9, abs=1e-9)`

## Required Edge Cases
- Handle NaN/invalid ratios explicitly.
- Protect boundary trimming behavior.
- Reject invalid inputs where required by the tests.
- Avoid brittle shortcuts that only satisfy one fixture.
