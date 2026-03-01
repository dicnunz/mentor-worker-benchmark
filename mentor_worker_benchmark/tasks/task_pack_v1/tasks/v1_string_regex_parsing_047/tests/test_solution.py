from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $velvet_7 then $willow5! repeat $VELVET_7 and punctuation $willow5,'
    assert extract_markers(text) == ['velvet_7', 'willow5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$kilo1 should be ignored; keep ($kilo1) and skip $xxx.'
    assert extract_markers(text) == ['kilo1']


def test_preserves_order() -> None:
    text = 'Noise ($pearl_2) plus $velvet_7. trailing $pearl_2,'
    assert extract_markers(text) == ['pearl_2', 'velvet_7']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
