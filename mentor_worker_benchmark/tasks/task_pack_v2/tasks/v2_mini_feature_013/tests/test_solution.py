from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-13-a:delta:active:4\\ntask-13-b:atlas:deferred:5\\ntask-13-c:delta:active:6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-13-c', 'task-13-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-13-a:delta:active:4\\ntask-13-b:atlas:deferred:5\\ntask-13-c:delta:active:6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-13-c', 'task-13-b', 'task-13-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-13-a:delta:active:4\\ntask-13-b:atlas:deferred:5\\ntask-13-c:delta:active:6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
