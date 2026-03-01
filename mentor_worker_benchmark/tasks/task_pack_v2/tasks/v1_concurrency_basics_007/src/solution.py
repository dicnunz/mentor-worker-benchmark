from collections.abc import Callable


def run_jobs(jobs: list[Callable[[], int]], max_workers: int) -> list[int]:
    if max_workers <= 0:
        raise ValueError("max_workers must be > 0")

    # Buggy starter: executes sequentially.
    return [job() for job in jobs]
