from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %thunder_3 then %blossom1! repeat %THUNDER_3 and punctuation %blossom1,'
    assert extract_markers(text) == ['thunder_3', 'blossom1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%river4 should be ignored; keep (%river4) and skip %xx.'
    assert extract_markers(text) == ['river4']


def test_preserves_order() -> None:
    text = 'Noise (%delta_8) plus %thunder_3. trailing %delta_8,'
    assert extract_markers(text) == ['delta_8', 'thunder_3']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
