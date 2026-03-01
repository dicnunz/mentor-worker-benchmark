from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #xenon_1 then #zebra3! repeat #XENON_1 and punctuation #zebra3,'
    assert extract_markers(text) == ['xenon_1', 'zebra3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#zephyr6 should be ignored; keep (#zephyr6) and skip #xx.'
    assert extract_markers(text) == ['zephyr6']


def test_preserves_order() -> None:
    text = 'Noise (#mango_6) plus #xenon_1. trailing #mango_6,'
    assert extract_markers(text) == ['mango_6', 'xenon_1']
