from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'nectarine -> 4\\nmaple->2\\nnectarine->3\\nbad_line_without_separator\\nsolace->6\\nmaple->not_an_int\\n'
    assert summarize(raw) == {'total': 15, 'unique_keys': 3, 'top_key': 'nectarine', 'top_value': 7}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
