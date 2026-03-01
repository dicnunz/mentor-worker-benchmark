from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #fable_1 then #yearling0! repeat #FABLE_1 and punctuation #yearling0,'
    assert extract_markers(text) == ['fable_1', 'yearling0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#dynamo3 should be ignored; keep (#dynamo3) and skip #x.'
    assert extract_markers(text) == ['dynamo3']


def test_preserves_order() -> None:
    text = 'Noise (#yonder_6) plus #fable_1. trailing #yonder_6,'
    assert extract_markers(text) == ['yonder_6', 'fable_1']
