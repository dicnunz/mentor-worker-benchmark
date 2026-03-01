from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $foxtrot_2 then $quiver1! repeat $FOXTROT_2 and punctuation $quiver1,'
    assert extract_markers(text) == ['foxtrot_2', 'quiver1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$india4 should be ignored; keep ($india4) and skip $xx.'
    assert extract_markers(text) == ['india4']


def test_preserves_order() -> None:
    text = 'Noise ($kepler_7) plus $foxtrot_2. trailing $kepler_7,'
    assert extract_markers(text) == ['kepler_7', 'foxtrot_2']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
