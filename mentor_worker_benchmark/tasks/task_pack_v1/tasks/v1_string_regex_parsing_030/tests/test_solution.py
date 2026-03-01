from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @apricot_0 then @alpha2! repeat @APRICOT_0 and punctuation @alpha2,'
    assert extract_markers(text) == ['apricot_0', 'alpha2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@cinder5 should be ignored; keep (@cinder5) and skip @x.'
    assert extract_markers(text) == ['cinder5']


def test_preserves_order() -> None:
    text = 'Noise (@fable_5) plus @apricot_0. trailing @fable_5,'
    assert extract_markers(text) == ['fable_5', 'apricot_0']
