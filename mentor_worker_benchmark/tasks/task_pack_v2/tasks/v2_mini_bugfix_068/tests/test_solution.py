from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('pioneer,5,core\\ntimber,7,edge\\nlumen,4,core\\ninvalid line\\npioneer,12,core', threshold=5)
    assert report["total"] == 28
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'pioneer'


def test_empty_input() -> None:
    report = build_report("", threshold=5)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
