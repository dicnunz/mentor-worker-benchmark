# Task: Concurrent Job Runner (hard)

Fix `run_jobs(jobs, max_workers)` in `src/solution.py`.

Requirements:
- Execute jobs concurrently (threading is acceptable).
- Preserve input order in the returned list.
- Raise `ValueError` if `max_workers <= 0`.
- Propagate job exceptions.
