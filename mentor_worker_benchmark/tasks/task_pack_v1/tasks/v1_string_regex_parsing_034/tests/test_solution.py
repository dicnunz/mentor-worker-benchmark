from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &umber_4 then &oasis6! repeat &UMBER_4 and punctuation &oasis6,'
    assert extract_markers(text) == ['umber_4', 'oasis6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&xylem2 should be ignored; keep (&xylem2) and skip &xx.'
    assert extract_markers(text) == ['xylem2']


def test_preserves_order() -> None:
    text = 'Noise (&sierra_9) plus &umber_4. trailing &sierra_9,'
    assert extract_markers(text) == ['sierra_9', 'umber_4']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
