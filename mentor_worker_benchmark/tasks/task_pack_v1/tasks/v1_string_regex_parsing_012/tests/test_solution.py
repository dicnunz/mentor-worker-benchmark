from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $rocket_2 then $quest5! repeat $ROCKET_2 and punctuation $quest5,'
    assert extract_markers(text) == ['rocket_2', 'quest5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$zebra1 should be ignored; keep ($zebra1) and skip $x.'
    assert extract_markers(text) == ['zebra1']


def test_preserves_order() -> None:
    text = 'Noise ($lotus_7) plus $rocket_2. trailing $lotus_7,'
    assert extract_markers(text) == ['lotus_7', 'rocket_2']
