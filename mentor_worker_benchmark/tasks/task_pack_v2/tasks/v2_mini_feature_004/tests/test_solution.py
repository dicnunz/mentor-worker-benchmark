from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-4-a:delta:active:3\\ntask-4-b:jade:deferred:4\\ntask-4-c:delta:active:6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-4-c', 'task-4-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-4-a:delta:active:3\\ntask-4-b:jade:deferred:4\\ntask-4-c:delta:active:6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-4-c', 'task-4-b', 'task-4-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-4-a:delta:active:3\\ntask-4-b:jade:deferred:4\\ntask-4-c:delta:active:6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
