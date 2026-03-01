from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @cobalt_5 then @timber1! repeat @COBALT_5 and punctuation @timber1,'
    assert extract_markers(text) == ['cobalt_5', 'timber1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@galaxy4 should be ignored; keep (@galaxy4) and skip @x.'
    assert extract_markers(text) == ['galaxy4']


def test_preserves_order() -> None:
    text = 'Noise (@orion_0) plus @cobalt_5. trailing @orion_0,'
    assert extract_markers(text) == ['orion_0', 'cobalt_5']
