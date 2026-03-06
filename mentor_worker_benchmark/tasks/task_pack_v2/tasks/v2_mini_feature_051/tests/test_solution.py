from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-51-a|cinder|active|4\\ntask-51-b|ion|deferred|5\\ntask-51-c|cinder|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-51-c', 'task-51-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-51-a|cinder|active|4\\ntask-51-b|ion|deferred|5\\ntask-51-c|cinder|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-51-c', 'task-51-b', 'task-51-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-51-a|cinder|active|4\\ntask-51-b|ion|deferred|5\\ntask-51-c|cinder|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
