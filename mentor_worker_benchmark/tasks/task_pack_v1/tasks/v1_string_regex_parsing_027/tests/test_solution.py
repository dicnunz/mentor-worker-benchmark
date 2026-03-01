from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $nebula_7 then $cobalt6! repeat $NEBULA_7 and punctuation $cobalt6,'
    assert extract_markers(text) == ['nebula_7', 'cobalt6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$meadow2 should be ignored; keep ($meadow2) and skip $x.'
    assert extract_markers(text) == ['meadow2']


def test_preserves_order() -> None:
    text = 'Noise ($beacon_2) plus $nebula_7. trailing $beacon_2,'
    assert extract_markers(text) == ['beacon_2', 'nebula_7']
