# Task: Concurrent Job Runner (medium)

Fix `run_jobs(jobs, max_workers)` in `src/solution.py`.

Requirements:
- Execute jobs concurrently (threading is acceptable).
- Preserve input order in the returned list.
- Raise `ValueError` if `max_workers <= 0`.
- Propagate job exceptions.

## Quality Gate Expectations
Implement all behavior required by tests, including edge-case handling and deterministic output.

## Input/Output Examples
- Example 1 input/output contract: `assert result == list(range(8))`
- Example 2 input/output contract: `assert elapsed < 0.137`

## Required Edge Cases
- Handle empty job lists and invalid worker counts.
- Preserve deterministic output ordering despite concurrency.
- Reject invalid inputs where required by the tests.
