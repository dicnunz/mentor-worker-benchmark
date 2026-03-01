from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'orion | 5\\nxenon|2\\norion|3\\nbad_line_without_separator\\namber|6\\nxenon|not_an_int\\n'
    assert summarize(raw) == {'total': 16, 'unique_keys': 3, 'top_key': 'orion', 'top_value': 8}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
