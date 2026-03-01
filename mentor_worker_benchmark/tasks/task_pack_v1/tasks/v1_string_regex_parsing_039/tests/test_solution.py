from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &pioneer_9 then &hotel4! repeat &PIONEER_9 and punctuation &hotel4,'
    assert extract_markers(text) == ['pioneer_9', 'hotel4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&onyx0 should be ignored; keep (&onyx0) and skip &x.'
    assert extract_markers(text) == ['onyx0']


def test_preserves_order() -> None:
    text = 'Noise (&temple_4) plus &pioneer_9. trailing &temple_4,'
    assert extract_markers(text) == ['temple_4', 'pioneer_9']
