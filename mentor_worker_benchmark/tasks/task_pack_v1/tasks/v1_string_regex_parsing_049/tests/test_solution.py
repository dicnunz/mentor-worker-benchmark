from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &unity_9 then &zen0! repeat &UNITY_9 and punctuation &zen0,'
    assert extract_markers(text) == ['unity_9', 'zen0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&glider3 should be ignored; keep (&glider3) and skip &xx.'
    assert extract_markers(text) == ['glider3']


def test_preserves_order() -> None:
    text = 'Noise (&dynamo_4) plus &unity_9. trailing &dynamo_4,'
    assert extract_markers(text) == ['dynamo_4', 'unity_9']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
