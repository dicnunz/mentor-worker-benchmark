from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #iris_6 then #blossom1! repeat #IRIS_6 and punctuation #blossom1,'
    assert extract_markers(text) == ['iris_6', 'blossom1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#temple4 should be ignored; keep (#temple4) and skip #x.'
    assert extract_markers(text) == ['temple4']


def test_preserves_order() -> None:
    text = 'Noise (#elm_1) plus #iris_6. trailing #elm_1,'
    assert extract_markers(text) == ['elm_1', 'iris_6']
