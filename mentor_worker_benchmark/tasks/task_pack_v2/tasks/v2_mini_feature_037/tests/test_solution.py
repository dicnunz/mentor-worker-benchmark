from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-37-a:pioneer:active:4\\ntask-37-b:ember:deferred:5\\ntask-37-c:pioneer:active:6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-37-c', 'task-37-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-37-a:pioneer:active:4\\ntask-37-b:ember:deferred:5\\ntask-37-c:pioneer:active:6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-37-c', 'task-37-b', 'task-37-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-37-a:pioneer:active:4\\ntask-37-b:ember:deferred:5\\ntask-37-c:pioneer:active:6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
