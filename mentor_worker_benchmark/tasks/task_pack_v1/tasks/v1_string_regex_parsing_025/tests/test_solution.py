from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @xenon_5 then @horizon4! repeat @XENON_5 and punctuation @horizon4,'
    assert extract_markers(text) == ['xenon_5', 'horizon4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@amber0 should be ignored; keep (@amber0) and skip @xx.'
    assert extract_markers(text) == ['amber0']


def test_preserves_order() -> None:
    text = 'Noise (@quiver_0) plus @xenon_5. trailing @quiver_0,'
    assert extract_markers(text) == ['quiver_0', 'xenon_5']
