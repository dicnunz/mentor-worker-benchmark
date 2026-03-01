from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $saffron_2 then $meadow1! repeat $SAFFRON_2 and punctuation $meadow1,'
    assert extract_markers(text) == ['saffron_2', 'meadow1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$lima4 should be ignored; keep ($lima4) and skip $xx.'
    assert extract_markers(text) == ['lima4']


def test_preserves_order() -> None:
    text = 'Noise ($ultra_7) plus $saffron_2. trailing $ultra_7,'
    assert extract_markers(text) == ['ultra_7', 'saffron_2']
