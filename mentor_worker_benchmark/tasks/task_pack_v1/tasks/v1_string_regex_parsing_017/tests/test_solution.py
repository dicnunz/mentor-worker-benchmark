from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $velvet_7 then $eagle3! repeat $VELVET_7 and punctuation $eagle3,'
    assert extract_markers(text) == ['velvet_7', 'eagle3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$vivid6 should be ignored; keep ($vivid6) and skip $xxx.'
    assert extract_markers(text) == ['vivid6']


def test_preserves_order() -> None:
    text = 'Noise ($dawn_2) plus $velvet_7. trailing $dawn_2,'
    assert extract_markers(text) == ['dawn_2', 'velvet_7']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
