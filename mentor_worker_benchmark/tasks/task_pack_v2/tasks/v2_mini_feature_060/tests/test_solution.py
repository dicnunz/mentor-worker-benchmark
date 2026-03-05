from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-60-a|onyx|active|3\\ntask-60-b|vector|deferred|4\\ntask-60-c|onyx|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-60-c', 'task-60-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-60-a|onyx|active|3\\ntask-60-b|vector|deferred|4\\ntask-60-c|onyx|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-60-c', 'task-60-b', 'task-60-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-60-a|onyx|active|3\\ntask-60-b|vector|deferred|4\\ntask-60-c|onyx|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
