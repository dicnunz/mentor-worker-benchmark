from .formatter import render
from .parser import parse_tasks
from .planner import build_plan


def generate_plan(
    raw: str,
    *,
    min_points: int = 0,
    include_deferred: bool = False,
    include_status_breakdown: bool = False,
) -> dict[str, object]:
    items = parse_tasks(raw)
    # Buggy: include_deferred not threaded through.
    plan = build_plan(items, min_points=min_points, include_deferred=False)
    if include_status_breakdown:
        # Buggy: missing real breakdown map.
        return render(plan, status_breakdown={})
    return render(plan)
