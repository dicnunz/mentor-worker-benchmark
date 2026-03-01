from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &ripple_4 then &delta3! repeat &RIPPLE_4 and punctuation &delta3,'
    assert extract_markers(text) == ['ripple_4', 'delta3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&opal6 should be ignored; keep (&opal6) and skip &x.'
    assert extract_markers(text) == ['opal6']


def test_preserves_order() -> None:
    text = 'Noise (&kernel_9) plus &ripple_4. trailing &kernel_9,'
    assert extract_markers(text) == ['kernel_9', 'ripple_4']
