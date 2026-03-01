from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &apricot_9 then &cobalt0! repeat &APRICOT_9 and punctuation &cobalt0,'
    assert extract_markers(text) == ['apricot_9', 'cobalt0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&thunder3 should be ignored; keep (&thunder3) and skip &xx.'
    assert extract_markers(text) == ['thunder3']


def test_preserves_order() -> None:
    text = 'Noise (&bravo_4) plus &apricot_9. trailing &bravo_4,'
    assert extract_markers(text) == ['bravo_4', 'apricot_9']
