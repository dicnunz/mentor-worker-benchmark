from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #rocket_1 then #utopia6! repeat #ROCKET_1 and punctuation #utopia6,'
    assert extract_markers(text) == ['rocket_1', 'utopia6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#thunder2 should be ignored; keep (#thunder2) and skip #xxx.'
    assert extract_markers(text) == ['thunder2']


def test_preserves_order() -> None:
    text = 'Noise (#juliet_6) plus #rocket_1. trailing #juliet_6,'
    assert extract_markers(text) == ['juliet_6', 'rocket_1']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
