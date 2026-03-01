from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &warden_4 then &charlie0! repeat &WARDEN_4 and punctuation &charlie0,'
    assert extract_markers(text) == ['warden_4', 'charlie0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&jade3 should be ignored; keep (&jade3) and skip &xxx.'
    assert extract_markers(text) == ['jade3']


def test_preserves_order() -> None:
    text = 'Noise (&hotel_9) plus &warden_4. trailing &hotel_9,'
    assert extract_markers(text) == ['hotel_9', 'warden_4']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
