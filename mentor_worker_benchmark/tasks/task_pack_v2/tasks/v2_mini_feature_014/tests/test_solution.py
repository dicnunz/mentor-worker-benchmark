from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-14-a=zenith=active=3\\ntask-14-b=jade=deferred=4\\ntask-14-c=zenith=active=6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-14-c', 'task-14-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-14-a=zenith=active=3\\ntask-14-b=jade=deferred=4\\ntask-14-c=zenith=active=6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-14-c', 'task-14-b', 'task-14-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-14-a=zenith=active=3\\ntask-14-b=jade=deferred=4\\ntask-14-c=zenith=active=6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
