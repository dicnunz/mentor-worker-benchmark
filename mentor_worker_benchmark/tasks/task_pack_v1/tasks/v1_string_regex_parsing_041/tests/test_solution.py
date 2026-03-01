from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #quill_1 then #kepler6! repeat #QUILL_1 and punctuation #kepler6,'
    assert extract_markers(text) == ['quill_1', 'kepler6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#amber2 should be ignored; keep (#amber2) and skip #xxx.'
    assert extract_markers(text) == ['amber2']


def test_preserves_order() -> None:
    text = 'Noise (#zenith_6) plus #quill_1. trailing #zenith_6,'
    assert extract_markers(text) == ['zenith_6', 'quill_1']
