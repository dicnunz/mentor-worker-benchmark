from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-26-a=onyx=active=3\\ntask-26-b=pioneer=deferred=4\\ntask-26-c=onyx=active=6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-26-c', 'task-26-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-26-a=onyx=active=3\\ntask-26-b=pioneer=deferred=4\\ntask-26-c=onyx=active=6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-26-c', 'task-26-b', 'task-26-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-26-a=onyx=active=3\\ntask-26-b=pioneer=deferred=4\\ntask-26-c=onyx=active=6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
