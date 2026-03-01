from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @glider_5 then @lotus0! repeat @GLIDER_5 and punctuation @lotus0,'
    assert extract_markers(text) == ['glider_5', 'lotus0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@whiskey3 should be ignored; keep (@whiskey3) and skip @xxx.'
    assert extract_markers(text) == ['whiskey3']


def test_preserves_order() -> None:
    text = 'Noise (@echo_0) plus @glider_5. trailing @echo_0,'
    assert extract_markers(text) == ['echo_0', 'glider_5']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
