from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @oasis_5 then @wander0! repeat @OASIS_5 and punctuation @wander0,'
    assert extract_markers(text) == ['oasis_5', 'wander0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@velvet3 should be ignored; keep (@velvet3) and skip @xxx.'
    assert extract_markers(text) == ['velvet3']


def test_preserves_order() -> None:
    text = 'Noise (@india_0) plus @oasis_5. trailing @india_0,'
    assert extract_markers(text) == ['india_0', 'oasis_5']
