from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-72-a|fable|active|3\\ntask-72-b|pioneer|deferred|4\\ntask-72-c|fable|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-72-c', 'task-72-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-72-a|fable|active|3\\ntask-72-b|pioneer|deferred|4\\ntask-72-c|fable|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-72-c', 'task-72-b', 'task-72-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-72-a|fable|active|3\\ntask-72-b|pioneer|deferred|4\\ntask-72-c|fable|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
