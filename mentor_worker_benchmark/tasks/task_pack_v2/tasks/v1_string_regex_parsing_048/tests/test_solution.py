from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %orion_8 then %beacon6! repeat %ORION_8 and punctuation %beacon6,'
    assert extract_markers(text) == ['orion_8', 'beacon6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%opal2 should be ignored; keep (%opal2) and skip %x.'
    assert extract_markers(text) == ['opal2']


def test_preserves_order() -> None:
    text = 'Noise (%hazel_3) plus %orion_8. trailing %hazel_3,'
    assert extract_markers(text) == ['hazel_3', 'orion_8']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
