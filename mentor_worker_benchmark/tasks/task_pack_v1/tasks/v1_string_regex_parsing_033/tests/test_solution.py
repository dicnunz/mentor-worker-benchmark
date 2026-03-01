from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %ripple_3 then %temple5! repeat %RIPPLE_3 and punctuation %temple5,'
    assert extract_markers(text) == ['ripple_3', 'temple5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%canyon1 should be ignored; keep (%canyon1) and skip %x.'
    assert extract_markers(text) == ['canyon1']


def test_preserves_order() -> None:
    text = 'Noise (%meadow_8) plus %ripple_3. trailing %meadow_8,'
    assert extract_markers(text) == ['meadow_8', 'ripple_3']
