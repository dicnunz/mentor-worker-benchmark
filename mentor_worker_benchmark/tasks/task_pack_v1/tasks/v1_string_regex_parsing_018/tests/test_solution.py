from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %whiskey_8 then %alpha4! repeat %WHISKEY_8 and punctuation %alpha4,'
    assert extract_markers(text) == ['whiskey_8', 'alpha4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%saffron0 should be ignored; keep (%saffron0) and skip %x.'
    assert extract_markers(text) == ['saffron0']


def test_preserves_order() -> None:
    text = 'Noise (%grove_3) plus %whiskey_8. trailing %grove_3,'
    assert extract_markers(text) == ['grove_3', 'whiskey_8']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
