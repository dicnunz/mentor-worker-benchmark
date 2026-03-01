from src.pipeline import summarize


def test_pipeline_summary_handles_invalid_lines() -> None:
    raw = 'drift -> 4\\ngalaxy->2\\ndrift->3\\nbad_line_without_separator\\nripple->6\\ngalaxy->not_an_int\\n'
    assert summarize(raw) == {'total': 15, 'unique_keys': 3, 'top_key': 'drift', 'top_value': 7}


def test_empty_input() -> None:
    assert summarize("") == {
        "total": 0,
        "unique_keys": 0,
        "top_key": None,
        "top_value": None,
    }
