from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &breeze_4 then &hazel3! repeat &BREEZE_4 and punctuation &hazel3,'
    assert extract_markers(text) == ['breeze_4', 'hazel3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&sierra6 should be ignored; keep (&sierra6) and skip &x.'
    assert extract_markers(text) == ['sierra6']


def test_preserves_order() -> None:
    text = 'Noise (&quest_9) plus &breeze_4. trailing &quest_9,'
    assert extract_markers(text) == ['quest_9', 'breeze_4']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
