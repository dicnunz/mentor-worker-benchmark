from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @orion_0 then @canyon0! repeat @ORION_0 and punctuation @canyon0,'
    assert extract_markers(text) == ['orion_0', 'canyon0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@kepler3 should be ignored; keep (@kepler3) and skip @x.'
    assert extract_markers(text) == ['kepler3']


def test_preserves_order() -> None:
    text = 'Noise (@eagle_5) plus @orion_0. trailing @eagle_5,'
    assert extract_markers(text) == ['eagle_5', 'orion_0']
