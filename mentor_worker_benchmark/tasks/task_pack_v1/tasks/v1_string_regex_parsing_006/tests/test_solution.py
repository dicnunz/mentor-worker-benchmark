from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #eagle_6 then #breeze6! repeat #EAGLE_6 and punctuation #breeze6,'
    assert extract_markers(text) == ['eagle_6', 'breeze6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#dynamo2 should be ignored; keep (#dynamo2) and skip #x.'
    assert extract_markers(text) == ['dynamo2']


def test_preserves_order() -> None:
    text = 'Noise (#kepler_1) plus #eagle_6. trailing #kepler_1,'
    assert extract_markers(text) == ['kepler_1', 'eagle_6']
