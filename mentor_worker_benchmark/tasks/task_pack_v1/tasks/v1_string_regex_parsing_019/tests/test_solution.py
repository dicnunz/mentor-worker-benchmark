from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &onyx_9 then &dynamo5! repeat &ONYX_9 and punctuation &dynamo5,'
    assert extract_markers(text) == ['onyx_9', 'dynamo5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&india1 should be ignored; keep (&india1) and skip &xx.'
    assert extract_markers(text) == ['india1']


def test_preserves_order() -> None:
    text = 'Noise (&jade_4) plus &onyx_9. trailing &jade_4,'
    assert extract_markers(text) == ['jade_4', 'onyx_9']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
