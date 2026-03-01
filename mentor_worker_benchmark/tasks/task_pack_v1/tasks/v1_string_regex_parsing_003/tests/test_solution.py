from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %thunder_3 then %elm3! repeat %THUNDER_3 and punctuation %elm3,'
    assert extract_markers(text) == ['thunder_3', 'elm3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%dawn6 should be ignored; keep (%dawn6) and skip %x.'
    assert extract_markers(text) == ['dawn6']


def test_preserves_order() -> None:
    text = 'Noise (%eagle_8) plus %thunder_3. trailing %eagle_8,'
    assert extract_markers(text) == ['eagle_8', 'thunder_3']
