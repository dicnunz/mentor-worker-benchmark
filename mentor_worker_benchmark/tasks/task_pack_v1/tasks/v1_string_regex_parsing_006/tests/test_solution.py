from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #rocket_6 then #kilo6! repeat #ROCKET_6 and punctuation #kilo6,'
    assert extract_markers(text) == ['rocket_6', 'kilo6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#bravo2 should be ignored; keep (#bravo2) and skip #x.'
    assert extract_markers(text) == ['bravo2']


def test_preserves_order() -> None:
    text = 'Noise (#utopia_1) plus #rocket_6. trailing #utopia_1,'
    assert extract_markers(text) == ['utopia_1', 'rocket_6']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
