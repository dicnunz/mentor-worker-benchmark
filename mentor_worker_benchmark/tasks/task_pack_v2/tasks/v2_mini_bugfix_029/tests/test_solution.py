from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('nova,6,core\\ntimber,8,edge\\nyonder,5,core\\ninvalid line\\nnova,13,core', threshold=6)
    assert report["total"] == 32
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'nova'


def test_empty_input() -> None:
    report = build_report("", threshold=6)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
