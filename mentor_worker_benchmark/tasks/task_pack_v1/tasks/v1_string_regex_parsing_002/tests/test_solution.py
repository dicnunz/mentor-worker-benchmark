from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $apricot_2 then $bravo2! repeat $APRICOT_2 and punctuation $bravo2,'
    assert extract_markers(text) == ['apricot_2', 'bravo2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$juliet5 should be ignored; keep ($juliet5) and skip $xxx.'
    assert extract_markers(text) == ['juliet5']


def test_preserves_order() -> None:
    text = 'Noise ($dynamo_7) plus $apricot_2. trailing $dynamo_7,'
    assert extract_markers(text) == ['dynamo_7', 'apricot_2']
