from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('atlas;8;core\\nxylem;10;edge\\njade;7;core\\ninvalid line\\natlas;15;core', threshold=8)
    assert report["total"] == 40
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'atlas'


def test_empty_input() -> None:
    report = build_report("", threshold=8)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
