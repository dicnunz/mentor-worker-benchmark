from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &beacon_9 then &rocket5! repeat &BEACON_9 and punctuation &rocket5,'
    assert extract_markers(text) == ['beacon_9', 'rocket5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&legend1 should be ignored; keep (&legend1) and skip &xx.'
    assert extract_markers(text) == ['legend1']


def test_preserves_order() -> None:
    text = 'Noise (&mango_4) plus &beacon_9. trailing &mango_4,'
    assert extract_markers(text) == ['mango_4', 'beacon_9']
