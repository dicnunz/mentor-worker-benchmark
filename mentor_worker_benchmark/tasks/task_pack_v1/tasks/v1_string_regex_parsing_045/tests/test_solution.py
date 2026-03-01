from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @lima_5 then @timber3! repeat @LIMA_5 and punctuation @timber3,'
    assert extract_markers(text) == ['lima_5', 'timber3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@golf6 should be ignored; keep (@golf6) and skip @x.'
    assert extract_markers(text) == ['golf6']


def test_preserves_order() -> None:
    text = 'Noise (@alpha_0) plus @lima_5. trailing @alpha_0,'
    assert extract_markers(text) == ['alpha_0', 'lima_5']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
