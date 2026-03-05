def generate_plan(
    raw: str,
    *,
    min_points: int = 0,
    include_deferred: bool = False,
    include_status_breakdown: bool = False,
) -> dict[str, object]:
    """Reference entrypoint for this task.

    The benchmark harness executes tests against src/service.py.
    """
    raise NotImplementedError("Implement in src/service.py and related src modules.")
