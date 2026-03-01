from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #temple_1 then #onyx1! repeat #TEMPLE_1 and punctuation #onyx1,'
    assert extract_markers(text) == ['temple_1', 'onyx1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#galaxy4 should be ignored; keep (#galaxy4) and skip #xx.'
    assert extract_markers(text) == ['galaxy4']


def test_preserves_order() -> None:
    text = 'Noise (#juliet_6) plus #temple_1. trailing #juliet_6,'
    assert extract_markers(text) == ['juliet_6', 'temple_1']
