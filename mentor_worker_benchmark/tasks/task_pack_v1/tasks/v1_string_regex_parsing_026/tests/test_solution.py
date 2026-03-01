from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #whiskey_6 then #wander5! repeat #WHISKEY_6 and punctuation #wander5,'
    assert extract_markers(text) == ['whiskey_6', 'wander5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#glider1 should be ignored; keep (#glider1) and skip #xxx.'
    assert extract_markers(text) == ['glider1']


def test_preserves_order() -> None:
    text = 'Noise (#yankee_1) plus #whiskey_6. trailing #yankee_1,'
    assert extract_markers(text) == ['yankee_1', 'whiskey_6']
