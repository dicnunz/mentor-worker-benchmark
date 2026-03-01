from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @lantern_5 then @juliet5! repeat @LANTERN_5 and punctuation @juliet5,'
    assert extract_markers(text) == ['lantern_5', 'juliet5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@knight1 should be ignored; keep (@knight1) and skip @xxx.'
    assert extract_markers(text) == ['knight1']


def test_preserves_order() -> None:
    text = 'Noise (@xpress_0) plus @lantern_5. trailing @xpress_0,'
    assert extract_markers(text) == ['xpress_0', 'lantern_5']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
