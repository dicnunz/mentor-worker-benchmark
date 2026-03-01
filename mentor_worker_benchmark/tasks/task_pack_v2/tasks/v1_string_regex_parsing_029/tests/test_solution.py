from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &mercury_9 then &river1! repeat &MERCURY_9 and punctuation &river1,'
    assert extract_markers(text) == ['mercury_9', 'river1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&cobalt4 should be ignored; keep (&cobalt4) and skip &xxx.'
    assert extract_markers(text) == ['cobalt4']


def test_preserves_order() -> None:
    text = 'Noise (&oasis_4) plus &mercury_9. trailing &oasis_4,'
    assert extract_markers(text) == ['oasis_4', 'mercury_9']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
