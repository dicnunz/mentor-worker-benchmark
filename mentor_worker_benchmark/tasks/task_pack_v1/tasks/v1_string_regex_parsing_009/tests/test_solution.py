from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &apricot_9 then &solace2! repeat &APRICOT_9 and punctuation &solace2,'
    assert extract_markers(text) == ['apricot_9', 'solace2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&jade5 should be ignored; keep (&jade5) and skip &x.'
    assert extract_markers(text) == ['jade5']


def test_preserves_order() -> None:
    text = 'Noise (&xpress_4) plus &apricot_9. trailing &xpress_4,'
    assert extract_markers(text) == ['xpress_4', 'apricot_9']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
