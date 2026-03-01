from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $temple_2 then $lantern4! repeat $TEMPLE_2 and punctuation $lantern4,'
    assert extract_markers(text) == ['temple_2', 'lantern4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$kernel0 should be ignored; keep ($kernel0) and skip $xxx.'
    assert extract_markers(text) == ['kernel0']


def test_preserves_order() -> None:
    text = 'Noise ($delta_7) plus $temple_2. trailing $delta_7,'
    assert extract_markers(text) == ['delta_7', 'temple_2']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
