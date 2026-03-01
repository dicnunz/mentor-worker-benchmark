from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #dynamo_1 then #lantern4! repeat #DYNAMO_1 and punctuation #lantern4,'
    assert extract_markers(text) == ['dynamo_1', 'lantern4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#nova0 should be ignored; keep (#nova0) and skip #xxx.'
    assert extract_markers(text) == ['nova0']


def test_preserves_order() -> None:
    text = 'Noise (#temple_6) plus #dynamo_1. trailing #temple_6,'
    assert extract_markers(text) == ['temple_6', 'dynamo_1']
