from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $temple_7 then $frost5! repeat $TEMPLE_7 and punctuation $frost5,'
    assert extract_markers(text) == ['temple_7', 'frost5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$nova1 should be ignored; keep ($nova1) and skip $xxx.'
    assert extract_markers(text) == ['nova1']


def test_preserves_order() -> None:
    text = 'Noise ($lotus_2) plus $temple_7. trailing $lotus_2,'
    assert extract_markers(text) == ['lotus_2', 'temple_7']
