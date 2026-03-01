from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &maple_4 then &piper6! repeat &MAPLE_4 and punctuation &piper6,'
    assert extract_markers(text) == ['maple_4', 'piper6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&kernel2 should be ignored; keep (&kernel2) and skip &xx.'
    assert extract_markers(text) == ['kernel2']


def test_preserves_order() -> None:
    text = 'Noise (&xenon_9) plus &maple_4. trailing &xenon_9,'
    assert extract_markers(text) == ['xenon_9', 'maple_4']
