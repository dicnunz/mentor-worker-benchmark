# Task: Rank Products (easy)

Fix `rank_products(records, k)` in `src/solution.py`.

`records` is a list of `(name, score_delta)` pairs.

Requirements:
- Aggregate score deltas per product name.
- Drop products with total score `<= 0`.
- Sort by total descending, then by product name ascending.
- Return only product names.
- Return at most `k` entries.
- If `k <= 0`, return `[]`.

## Input/Output Examples
- `rank_products([("a", 2), ("b", 1), ("a", -1)], 2) == ["a", "b"]`
- `rank_products([("x", 1), ("y", 1)], 1) == ["x"]`
