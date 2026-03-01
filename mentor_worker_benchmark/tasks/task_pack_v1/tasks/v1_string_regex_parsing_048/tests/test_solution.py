from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %quest_8 then %temple6! repeat %QUEST_8 and punctuation %temple6,'
    assert extract_markers(text) == ['quest_8', 'temple6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%prairie2 should be ignored; keep (%prairie2) and skip %x.'
    assert extract_markers(text) == ['prairie2']


def test_preserves_order() -> None:
    text = 'Noise (%drift_3) plus %quest_8. trailing %drift_3,'
    assert extract_markers(text) == ['drift_3', 'quest_8']
