from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &island_4 then &quest4! repeat &ISLAND_4 and punctuation &quest4,'
    assert extract_markers(text) == ['island_4', 'quest4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&beacon0 should be ignored; keep (&beacon0) and skip &xx.'
    assert extract_markers(text) == ['beacon0']


def test_preserves_order() -> None:
    text = 'Noise (&onyx_9) plus &island_4. trailing &onyx_9,'
    assert extract_markers(text) == ['onyx_9', 'island_4']
