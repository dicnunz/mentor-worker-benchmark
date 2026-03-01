from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &orion_4 then &warden4! repeat &ORION_4 and punctuation &warden4,'
    assert extract_markers(text) == ['orion_4', 'warden4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&echo0 should be ignored; keep (&echo0) and skip &xx.'
    assert extract_markers(text) == ['echo0']


def test_preserves_order() -> None:
    text = 'Noise (&ember_9) plus &orion_4. trailing &ember_9,'
    assert extract_markers(text) == ['ember_9', 'orion_4']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
