from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-74-a=signal=active=3\\ntask-74-b=cinder=deferred=4\\ntask-74-c=signal=active=6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-74-c', 'task-74-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-74-a=signal=active=3\\ntask-74-b=cinder=deferred=4\\ntask-74-c=signal=active=6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-74-c', 'task-74-b', 'task-74-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-74-a=signal=active=3\\ntask-74-b=cinder=deferred=4\\ntask-74-c=signal=active=6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
