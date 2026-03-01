from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &quest_9 then &saffron1! repeat &QUEST_9 and punctuation &saffron1,'
    assert extract_markers(text) == ['quest_9', 'saffron1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&eagle4 should be ignored; keep (&eagle4) and skip &xxx.'
    assert extract_markers(text) == ['eagle4']


def test_preserves_order() -> None:
    text = 'Noise (&nectar_4) plus &quest_9. trailing &nectar_4,'
    assert extract_markers(text) == ['nectar_4', 'quest_9']
