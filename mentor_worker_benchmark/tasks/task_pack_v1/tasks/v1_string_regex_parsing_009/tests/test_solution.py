from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &india_9 then &warden2! repeat &INDIA_9 and punctuation &warden2,'
    assert extract_markers(text) == ['india_9', 'warden2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&quartz5 should be ignored; keep (&quartz5) and skip &x.'
    assert extract_markers(text) == ['quartz5']


def test_preserves_order() -> None:
    text = 'Noise (&wander_4) plus &india_9. trailing &wander_4,'
    assert extract_markers(text) == ['wander_4', 'india_9']
