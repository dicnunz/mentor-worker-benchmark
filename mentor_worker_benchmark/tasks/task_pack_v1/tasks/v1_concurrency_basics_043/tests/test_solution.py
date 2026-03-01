import time

import pytest

from src.solution import run_jobs


def _make_job(value: int, delay: float):
    def _job() -> int:
        time.sleep(delay)
        return value

    return _job


def test_parallel_execution_is_faster_than_sequential() -> None:
    jobs = [_make_job(i, 0.026) for i in range(9)]
    start = time.perf_counter()
    result = run_jobs(jobs, max_workers=4)
    elapsed = time.perf_counter() - start

    assert result == list(range(9))
    assert elapsed < 0.183


def test_invalid_max_workers_raises() -> None:
    with pytest.raises(ValueError):
        run_jobs([], max_workers=0)


def test_exceptions_are_propagated() -> None:
    def ok() -> int:
        return 1

    def boom() -> int:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_jobs([ok, boom], max_workers=2)
