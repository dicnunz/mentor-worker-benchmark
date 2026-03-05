from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-87-a|onyx|active|4\\ntask-87-b|nova|deferred|5\\ntask-87-c|onyx|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-87-c', 'task-87-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-87-a|onyx|active|4\\ntask-87-b|nova|deferred|5\\ntask-87-c|onyx|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-87-c', 'task-87-b', 'task-87-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-87-a|onyx|active|4\\ntask-87-b|nova|deferred|5\\ntask-87-c|onyx|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
