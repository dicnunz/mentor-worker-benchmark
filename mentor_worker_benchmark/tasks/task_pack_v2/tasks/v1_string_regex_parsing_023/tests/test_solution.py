from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %umber_3 then %glider2! repeat %UMBER_3 and punctuation %glider2,'
    assert extract_markers(text) == ['umber_3', 'glider2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%willow5 should be ignored; keep (%willow5) and skip %xxx.'
    assert extract_markers(text) == ['willow5']


def test_preserves_order() -> None:
    text = 'Noise (%jasper_8) plus %umber_3. trailing %jasper_8,'
    assert extract_markers(text) == ['jasper_8', 'umber_3']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
