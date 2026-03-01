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
