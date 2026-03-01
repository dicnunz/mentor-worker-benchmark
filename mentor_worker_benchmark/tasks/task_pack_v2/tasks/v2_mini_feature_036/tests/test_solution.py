from src.service import generate_plan


def test_existing_behavior_without_feature_flags() -> None:
    payload = generate_plan('task-36-a|beacon|active|3\\ntask-36-b|xylem|deferred|4\\ntask-36-c|beacon|active|6\\nbad row', min_points=0)
    assert payload["tasks"] == ['task-36-c', 'task-36-a']


def test_include_deferred_feature() -> None:
    payload = generate_plan('task-36-a|beacon|active|3\\ntask-36-b|xylem|deferred|4\\ntask-36-c|beacon|active|6\\nbad row', min_points=0, include_deferred=True)
    assert payload["tasks"] == ['task-36-c', 'task-36-b', 'task-36-a']


def test_status_breakdown_feature() -> None:
    payload = generate_plan(
        'task-36-a|beacon|active|3\\ntask-36-b|xylem|deferred|4\\ntask-36-c|beacon|active|6\\nbad row',
        min_points=0,
        include_deferred=True,
        include_status_breakdown=True,
    )
    assert payload["status_breakdown"] == {"active": 2, "deferred": 1}
