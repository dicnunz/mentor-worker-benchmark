from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &solace_4 then &hazel2! repeat &SOLACE_4 and punctuation &hazel2,'
    assert extract_markers(text) == ['solace_4', 'hazel2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&legend5 should be ignored; keep (&legend5) and skip &xxx.'
    assert extract_markers(text) == ['legend5']


def test_preserves_order() -> None:
    text = 'Noise (&thunder_9) plus &solace_4. trailing &thunder_9,'
    assert extract_markers(text) == ['thunder_9', 'solace_4']
