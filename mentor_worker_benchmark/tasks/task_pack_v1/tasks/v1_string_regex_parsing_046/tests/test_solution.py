from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #voyage_6 then #xylem4! repeat #VOYAGE_6 and punctuation #xylem4,'
    assert extract_markers(text) == ['voyage_6', 'xylem4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#fable0 should be ignored; keep (#fable0) and skip #xx.'
    assert extract_markers(text) == ['fable0']


def test_preserves_order() -> None:
    text = 'Noise (#xenon_1) plus #voyage_6. trailing #xenon_1,'
    assert extract_markers(text) == ['xenon_1', 'voyage_6']
