from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @nova_5 then @kilo5! repeat @NOVA_5 and punctuation @kilo5,'
    assert extract_markers(text) == ['nova_5', 'kilo5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@orion1 should be ignored; keep (@orion1) and skip @xxx.'
    assert extract_markers(text) == ['orion1']


def test_preserves_order() -> None:
    text = 'Noise (@vertex_0) plus @nova_5. trailing @vertex_0,'
    assert extract_markers(text) == ['vertex_0', 'nova_5']
