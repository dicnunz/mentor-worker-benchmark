from pathlib import Path

from src.pipeline import summarize_from_report


def test_warn_threshold() -> None:
    report_path = Path("data/analyzer_output.txt")
    summary = summarize_from_report(str(report_path), min_severity="warn")
    assert summary["count"] == 3
    assert summary["by_severity"] == {"error": 1, "warn": 2}
    assert summary["top_rule"] == "unused_import"


def test_error_threshold() -> None:
    report_path = Path("data/analyzer_output.txt")
    summary = summarize_from_report(str(report_path), min_severity="error")
    assert summary["count"] == 1
    assert summary["by_severity"] == {"error": 1}
    assert summary["top_rule"] == "unsafe_eval"
