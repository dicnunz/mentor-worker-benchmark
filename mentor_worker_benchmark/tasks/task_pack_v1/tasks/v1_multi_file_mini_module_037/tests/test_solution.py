from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'hotel = 5\\nlegend=2\\nhotel=3\\nbad_line_without_separator\\ntimber=6\\nlegend=not_an_int\\n'
    assert summarize(raw) == {'total': 16, 'unique_keys': 3, 'top_key': 'hotel', 'top_value': 8}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
