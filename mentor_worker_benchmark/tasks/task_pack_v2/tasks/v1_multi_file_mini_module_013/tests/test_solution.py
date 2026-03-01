from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'zen = 5\\nlegend=2\\nzen=3\\nbad_line_without_separator\\nquartz=6\\nlegend=not_an_int\\n'
    assert summarize(raw) == {'total': 16, 'unique_keys': 3, 'top_key': 'zen', 'top_value': 8}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }

def test_malformed_only_input_returns_empty_report() -> None:
    assert summarize("invalid line only") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }

def test_trailing_blank_lines_are_safe() -> None:
    payload = summarize("\n\n")
    assert payload["total"] == 0
    assert payload["unique_keys"] == 0
