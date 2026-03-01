from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #umber_1 then #knight3! repeat #UMBER_1 and punctuation #knight3,'
    assert extract_markers(text) == ['umber_1', 'knight3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#hazel6 should be ignored; keep (#hazel6) and skip #xx.'
    assert extract_markers(text) == ['hazel6']


def test_preserves_order() -> None:
    text = 'Noise (#temple_6) plus #umber_1. trailing #temple_6,'
    assert extract_markers(text) == ['temple_6', 'umber_1']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
