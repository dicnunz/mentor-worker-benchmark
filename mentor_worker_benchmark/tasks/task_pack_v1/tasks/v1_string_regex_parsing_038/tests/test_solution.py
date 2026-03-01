from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %voyage_8 then %utopia3! repeat %VOYAGE_8 and punctuation %utopia3,'
    assert extract_markers(text) == ['voyage_8', 'utopia3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%alpha6 should be ignored; keep (%alpha6) and skip %xxx.'
    assert extract_markers(text) == ['alpha6']


def test_preserves_order() -> None:
    text = 'Noise (%pearl_3) plus %voyage_8. trailing %pearl_3,'
    assert extract_markers(text) == ['pearl_3', 'voyage_8']
