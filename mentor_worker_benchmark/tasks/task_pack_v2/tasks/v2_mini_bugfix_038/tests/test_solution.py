from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('timber,7,core\\ngrove,9,edge\\nkepler,6,core\\ninvalid line\\ntimber,14,core', threshold=7)
    assert report["total"] == 36
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'timber'


def test_empty_input() -> None:
    report = build_report("", threshold=7)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
