from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &foxtrot_9 then &glider4! repeat &FOXTROT_9 and punctuation &glider4,'
    assert extract_markers(text) == ['foxtrot_9', 'glider4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&lantern0 should be ignored; keep (&lantern0) and skip &x.'
    assert extract_markers(text) == ['lantern0']


def test_preserves_order() -> None:
    text = 'Noise (&bravo_4) plus &foxtrot_9. trailing &bravo_4,'
    assert extract_markers(text) == ['bravo_4', 'foxtrot_9']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
