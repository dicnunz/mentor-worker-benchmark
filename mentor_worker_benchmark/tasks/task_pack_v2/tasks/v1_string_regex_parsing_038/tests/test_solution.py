from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %xpress_8 then %hotel3! repeat %XPRESS_8 and punctuation %hotel3,'
    assert extract_markers(text) == ['xpress_8', 'hotel3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%opal6 should be ignored; keep (%opal6) and skip %xxx.'
    assert extract_markers(text) == ['opal6']


def test_preserves_order() -> None:
    text = 'Noise (%india_3) plus %xpress_8. trailing %india_3,'
    assert extract_markers(text) == ['india_3', 'xpress_8']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
