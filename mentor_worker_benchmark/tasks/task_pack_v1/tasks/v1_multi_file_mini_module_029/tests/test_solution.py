from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'opal = 6\\nhotel=2\\nopal=3\\nbad_line_without_separator\\nunity=6\\nhotel=not_an_int\\n'
    assert summarize(raw) == {'total': 17, 'unique_keys': 3, 'top_key': 'opal', 'top_value': 9}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
