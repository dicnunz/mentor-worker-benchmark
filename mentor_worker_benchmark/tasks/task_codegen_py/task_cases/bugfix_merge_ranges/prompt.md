# Task: Bugfix `merge_ranges`

Fix `merge_ranges` in `src/solution.py`.

Behavior:
- Input is a list of integer intervals `(start, end)`.
- Return merged intervals sorted by start.
- Overlapping OR touching intervals must merge. For example `(1,3)` and `(4,5)` should merge to `(1,5)`.
