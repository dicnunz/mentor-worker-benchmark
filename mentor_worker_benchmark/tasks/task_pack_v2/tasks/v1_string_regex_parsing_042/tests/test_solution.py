from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $prairie_2 then $galaxy0! repeat $PRAIRIE_2 and punctuation $galaxy0,'
    assert extract_markers(text) == ['prairie_2', 'galaxy0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$beacon3 should be ignored; keep ($beacon3) and skip $x.'
    assert extract_markers(text) == ['beacon3']


def test_preserves_order() -> None:
    text = 'Noise ($zen_7) plus $prairie_2. trailing $zen_7,'
    assert extract_markers(text) == ['zen_7', 'prairie_2']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
