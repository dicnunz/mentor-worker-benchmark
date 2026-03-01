from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('atlas|5|core\\nnova|7|edge\\nkepler|4|core\\ninvalid line\\natlas|12|core', threshold=5)
    assert report["total"] == 28
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'atlas'


def test_empty_input() -> None:
    report = build_report("", threshold=5)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
