from src.pipeline import build_report


def test_integration_report() -> None:
    report = build_report('delta;8;core\\njade;10;edge\\nember;7;core\\ninvalid line\\ndelta;15;core', threshold=8)
    assert report["total"] == 40
    assert report["count"] == 4
    assert report["above_threshold"] == 2
    assert report["top_label"] == 'delta'


def test_empty_input() -> None:
    report = build_report("", threshold=8)
    assert report == {
        "total": 0,
        "count": 0,
        "above_threshold": 0,
        "top_label": None,
    }
