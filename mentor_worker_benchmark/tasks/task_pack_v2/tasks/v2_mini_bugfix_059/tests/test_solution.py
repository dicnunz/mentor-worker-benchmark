from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('cinder,8,core\\nfable,10,edge\\npioneer,7,core\\ninvalid line\\ncinder,15,core', threshold=8)
    assert report["total"] == 40
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'cinder'


def test_empty_input() -> None:
    report = build_report("", threshold=8)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
