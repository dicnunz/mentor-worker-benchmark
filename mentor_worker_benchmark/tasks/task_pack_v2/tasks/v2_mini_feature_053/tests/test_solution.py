from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-53-a=willow=active=4\\ntask-53-b=timber=deferred=5\\ntask-53-c=willow=active=6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-53-c', 'task-53-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-53-a=willow=active=4\\ntask-53-b=timber=deferred=5\\ntask-53-c=willow=active=6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-53-c', 'task-53-b', 'task-53-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-53-a=willow=active=4\\ntask-53-b=timber=deferred=5\\ntask-53-c=willow=active=6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
