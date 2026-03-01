from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-44-a=atlas=active=3\\ntask-44-b=nova=deferred=4\\ntask-44-c=atlas=active=6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-44-c', 'task-44-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-44-a=atlas=active=3\\ntask-44-b=nova=deferred=4\\ntask-44-c=atlas=active=6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-44-c', 'task-44-b', 'task-44-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-44-a=atlas=active=3\\ntask-44-b=nova=deferred=4\\ntask-44-c=atlas=active=6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
