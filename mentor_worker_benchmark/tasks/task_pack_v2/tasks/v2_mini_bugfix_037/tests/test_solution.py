from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('pioneer;6;core\\nion;8;edge\\ngrove;5;core\\ninvalid line\\npioneer;13;core', threshold=6)
    assert report["total"] == 32
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'pioneer'


def test_empty_input() -> None:
    report = build_report("", threshold=6)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
