from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %xenon_8 then %vertex1! repeat %XENON_8 and punctuation %vertex1,'
    assert extract_markers(text) == ['xenon_8', 'vertex1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%yearling4 should be ignored; keep (%yearling4) and skip %xxx.'
    assert extract_markers(text) == ['yearling4']


def test_preserves_order() -> None:
    text = 'Noise (%mango_3) plus %xenon_8. trailing %mango_3,'
    assert extract_markers(text) == ['mango_3', 'xenon_8']
