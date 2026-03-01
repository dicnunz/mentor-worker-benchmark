from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-0-a|umbra|active|3\\ntask-0-b|timber|deferred|4\\ntask-0-c|umbra|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-0-c', 'task-0-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-0-a|umbra|active|3\\ntask-0-b|timber|deferred|4\\ntask-0-c|umbra|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-0-c', 'task-0-b', 'task-0-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-0-a|umbra|active|3\\ntask-0-b|timber|deferred|4\\ntask-0-c|umbra|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
