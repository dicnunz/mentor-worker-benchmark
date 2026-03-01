from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #ember_1 then #beacon1! repeat #EMBER_1 and punctuation #beacon1,'
    assert extract_markers(text) == ['ember_1', 'beacon1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#dawn4 should be ignored; keep (#dawn4) and skip #xx.'
    assert extract_markers(text) == ['dawn4']


def test_preserves_order() -> None:
    text = 'Noise (#fable_6) plus #ember_1. trailing #fable_6,'
    assert extract_markers(text) == ['fable_6', 'ember_1']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
