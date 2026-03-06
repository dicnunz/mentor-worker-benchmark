from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('umbra|7|core\\nfable|9|edge\\nember|6|core\\ninvalid line\\numbra|14|core', threshold=7)
    assert report["total"] == 36
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'umbra'


def test_empty_input() -> None:
    report = build_report("", threshold=7)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
