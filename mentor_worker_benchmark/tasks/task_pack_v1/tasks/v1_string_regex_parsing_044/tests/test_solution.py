from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &ivory_4 then &juliet2! repeat &IVORY_4 and punctuation &juliet2,'
    assert extract_markers(text) == ['ivory_4', 'juliet2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&jade5 should be ignored; keep (&jade5) and skip &xxx.'
    assert extract_markers(text) == ['jade5']


def test_preserves_order() -> None:
    text = 'Noise (&yearling_9) plus &ivory_4. trailing &yearling_9,'
    assert extract_markers(text) == ['yearling_9', 'ivory_4']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
