from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('timber,6,core\\nkepler,8,edge\\npioneer,5,core\\ninvalid line\\ntimber,13,core', threshold=6)
    assert report["total"] == 32
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'timber'


def test_empty_input() -> None:
    report = build_report("", threshold=6)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
