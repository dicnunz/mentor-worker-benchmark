# Task: Rank Products (hard)

Fix `rank_products(records, k)` in `src/solution.py`.

`records` is a list of `(name, score_delta)` pairs.

Requirements:
- Aggregate score deltas by product name.
- Drop products with total score `<= 0`.
- Sort by total descending, then by product name ascending.
- Return only product names.
- Return at most `k` entries.
- If `k <= 0`, return `[]`.

## Quality Gate Expectations
Implement all behavior required by tests, including edge-case handling and deterministic output.

## Input/Output Examples
- Example 1 input/output contract: `assert rank_products(records, 3) == ['willow', 'drift', 'xenon']`
- Example 2 input/output contract: `assert rank_products(records, 2) == ['voyage', 'drift']`

## Required Edge Cases
- Handle empty datasets and non-positive limits.
- Keep tie-breaking deterministic.
- Reject invalid inputs where required by the tests.
- Avoid brittle shortcuts that only satisfy one fixture.
