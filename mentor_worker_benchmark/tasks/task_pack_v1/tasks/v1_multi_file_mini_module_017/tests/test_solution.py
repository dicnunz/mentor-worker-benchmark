from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'india = 6\\nbravo=2\\nindia=3\\nbad_line_without_separator\\nlegend=6\\nbravo=not_an_int\\n'
    assert summarize(raw) == {'total': 17, 'unique_keys': 3, 'top_key': 'india', 'top_value': 9}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
