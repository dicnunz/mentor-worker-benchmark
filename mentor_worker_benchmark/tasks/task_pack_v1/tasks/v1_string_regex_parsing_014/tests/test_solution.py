from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff &lantern_4 then &rocket0! repeat &LANTERN_4 and punctuation &rocket0,'
    assert extract_markers(text) == ['lantern_4', 'rocket0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded&alpha3 should be ignored; keep (&alpha3) and skip &xxx.'
    assert extract_markers(text) == ['alpha3']


def test_preserves_order() -> None:
    text = 'Noise (&acorn_9) plus &lantern_4. trailing &acorn_9,'
    assert extract_markers(text) == ['acorn_9', 'lantern_4']
