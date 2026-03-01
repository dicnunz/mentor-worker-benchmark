from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @ultra_0 then @quest3! repeat @ULTRA_0 and punctuation @quest3,'
    assert extract_markers(text) == ['ultra_0', 'quest3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@feather6 should be ignored; keep (@feather6) and skip @xx.'
    assert extract_markers(text) == ['feather6']


def test_preserves_order() -> None:
    text = 'Noise (@bravo_5) plus @ultra_0. trailing @bravo_5,'
    assert extract_markers(text) == ['bravo_5', 'ultra_0']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
