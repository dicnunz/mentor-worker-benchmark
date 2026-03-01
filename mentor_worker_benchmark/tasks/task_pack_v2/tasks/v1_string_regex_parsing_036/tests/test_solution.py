from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #oasis_6 then #ivory1! repeat #OASIS_6 and punctuation #ivory1,'
    assert extract_markers(text) == ['oasis_6', 'ivory1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#feather4 should be ignored; keep (#feather4) and skip #x.'
    assert extract_markers(text) == ['feather4']


def test_preserves_order() -> None:
    text = 'Noise (#grove_1) plus #oasis_6. trailing #grove_1,'
    assert extract_markers(text) == ['grove_1', 'oasis_6']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
