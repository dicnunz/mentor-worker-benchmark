from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #nova_1 then #delta4! repeat #NOVA_1 and punctuation #delta4,'
    assert extract_markers(text) == ['nova_1', 'delta4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#pearl0 should be ignored; keep (#pearl0) and skip #xxx.'
    assert extract_markers(text) == ['pearl0']


def test_preserves_order() -> None:
    text = 'Noise (#bravo_6) plus #nova_1. trailing #bravo_6,'
    assert extract_markers(text) == ['bravo_6', 'nova_1']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
