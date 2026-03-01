from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #piper_6 then #quill2! repeat #PIPER_6 and punctuation #quill2,'
    assert extract_markers(text) == ['piper_6', 'quill2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#zephyr5 should be ignored; keep (#zephyr5) and skip #xx.'
    assert extract_markers(text) == ['zephyr5']


def test_preserves_order() -> None:
    text = 'Noise (#ultra_1) plus #piper_6. trailing #ultra_1,'
    assert extract_markers(text) == ['ultra_1', 'piper_6']
