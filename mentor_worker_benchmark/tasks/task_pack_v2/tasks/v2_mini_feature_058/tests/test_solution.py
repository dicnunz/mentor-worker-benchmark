from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-58-a:delta:active:3\\ntask-58-b:kepler:deferred:4\\ntask-58-c:delta:active:6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-58-c', 'task-58-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-58-a:delta:active:3\\ntask-58-b:kepler:deferred:4\\ntask-58-c:delta:active:6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-58-c', 'task-58-b', 'task-58-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-58-a:delta:active:3\\ntask-58-b:kepler:deferred:4\\ntask-58-c:delta:active:6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
