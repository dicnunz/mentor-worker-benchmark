from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-45-a|lumen|active|4\\ntask-45-b|signal|deferred|5\\ntask-45-c|lumen|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-45-c', 'task-45-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-45-a|lumen|active|4\\ntask-45-b|signal|deferred|5\\ntask-45-c|lumen|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-45-c', 'task-45-b', 'task-45-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-45-a|lumen|active|4\\ntask-45-b|signal|deferred|5\\ntask-45-c|lumen|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
