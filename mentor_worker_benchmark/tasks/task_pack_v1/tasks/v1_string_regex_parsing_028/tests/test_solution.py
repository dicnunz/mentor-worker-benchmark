from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %xylem_8 then %temple0! repeat %XYLEM_8 and punctuation %temple0,'
    assert extract_markers(text) == ['xylem_8', 'temple0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%quest3 should be ignored; keep (%quest3) and skip %xx.'
    assert extract_markers(text) == ['quest3']


def test_preserves_order() -> None:
    text = 'Noise (%saffron_3) plus %xylem_8. trailing %saffron_3,'
    assert extract_markers(text) == ['saffron_3', 'xylem_8']
