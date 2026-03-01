from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @warden_0 then @ripple5! repeat @WARDEN_0 and punctuation @ripple5,'
    assert extract_markers(text) == ['warden_0', 'ripple5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@sunset1 should be ignored; keep (@sunset1) and skip @xx.'
    assert extract_markers(text) == ['sunset1']


def test_preserves_order() -> None:
    text = 'Noise (@vertex_5) plus @warden_0. trailing @vertex_5,'
    assert extract_markers(text) == ['vertex_5', 'warden_0']
