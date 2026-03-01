from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-25-a:willow:active:4\\ntask-25-b:lumen:deferred:5\\ntask-25-c:willow:active:6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-25-c', 'task-25-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-25-a:willow:active:4\\ntask-25-b:lumen:deferred:5\\ntask-25-c:willow:active:6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-25-c', 'task-25-b', 'task-25-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-25-a:willow:active:4\\ntask-25-b:lumen:deferred:5\\ntask-25-c:willow:active:6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
