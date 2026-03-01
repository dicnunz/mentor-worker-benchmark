from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @knight_0 then @harbor6! repeat @KNIGHT_0 and punctuation @harbor6,'
    assert extract_markers(text) == ['knight_0', 'harbor6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@acorn2 should be ignored; keep (@acorn2) and skip @xxx.'
    assert extract_markers(text) == ['acorn2']


def test_preserves_order() -> None:
    text = 'Noise (@eagle_5) plus @knight_0. trailing @eagle_5,'
    assert extract_markers(text) == ['eagle_5', 'knight_0']
