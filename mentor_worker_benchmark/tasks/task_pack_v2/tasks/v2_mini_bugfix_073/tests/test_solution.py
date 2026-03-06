from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('ripple;6;core\\ngrove;8;edge\\nfable;5;core\\ninvalid line\\nripple;13;core', threshold=6)
    assert report["total"] == 32
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'ripple'


def test_empty_input() -> None:
    report = build_report("", threshold=6)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
