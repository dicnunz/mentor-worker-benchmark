from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @dynamo_0 then @frost5! repeat @DYNAMO_0 and punctuation @frost5,'
    assert extract_markers(text) == ['dynamo_0', 'frost5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@golf1 should be ignored; keep (@golf1) and skip @xx.'
    assert extract_markers(text) == ['golf1']


def test_preserves_order() -> None:
    text = 'Noise (@kilo_5) plus @dynamo_0. trailing @kilo_5,'
    assert extract_markers(text) == ['kilo_5', 'dynamo_0']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
