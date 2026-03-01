from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'zenith -> 5\\number->2\\nzenith->3\\nbad_line_without_separator\\nwhiskey->6\\number->not_an_int\\n'
    assert summarize(raw) == {'total': 16, 'unique_keys': 3, 'top_key': 'zenith', 'top_value': 8}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
