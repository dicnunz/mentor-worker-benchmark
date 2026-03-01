from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-28-a:pioneer:active:3\\ntask-28-b:quartz:deferred:4\\ntask-28-c:pioneer:active:6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-28-c', 'task-28-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-28-a:pioneer:active:3\\ntask-28-b:quartz:deferred:4\\ntask-28-c:pioneer:active:6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-28-c', 'task-28-b', 'task-28-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-28-a:pioneer:active:3\\ntask-28-b:quartz:deferred:4\\ntask-28-c:pioneer:active:6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
