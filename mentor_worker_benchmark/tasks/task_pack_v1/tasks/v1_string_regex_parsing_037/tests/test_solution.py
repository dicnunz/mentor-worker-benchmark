from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $cinder_7 then $river2! repeat $CINDER_7 and punctuation $river2,'
    assert extract_markers(text) == ['cinder_7', 'river2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$charlie5 should be ignored; keep ($charlie5) and skip $xx.'
    assert extract_markers(text) == ['charlie5']


def test_preserves_order() -> None:
    text = 'Noise ($grove_2) plus $cinder_7. trailing $grove_2,'
    assert extract_markers(text) == ['grove_2', 'cinder_7']
