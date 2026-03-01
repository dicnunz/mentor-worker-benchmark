from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-30-a|zenith|active|3\\ntask-30-b|jade|deferred|4\\ntask-30-c|zenith|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-30-c', 'task-30-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-30-a|zenith|active|3\\ntask-30-b|jade|deferred|4\\ntask-30-c|zenith|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-30-c', 'task-30-b', 'task-30-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-30-a|zenith|active|3\\ntask-30-b|jade|deferred|4\\ntask-30-c|zenith|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
