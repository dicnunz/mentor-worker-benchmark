from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @vertex_5 then @jade1! repeat @VERTEX_5 and punctuation @jade1,'
    assert extract_markers(text) == ['vertex_5', 'jade1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@eagle4 should be ignored; keep (@eagle4) and skip @x.'
    assert extract_markers(text) == ['eagle4']


def test_preserves_order() -> None:
    text = 'Noise (@thunder_0) plus @vertex_5. trailing @thunder_0,'
    assert extract_markers(text) == ['thunder_0', 'vertex_5']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
