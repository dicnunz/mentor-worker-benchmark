from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $onyx_7 then $horizon3! repeat $ONYX_7 and punctuation $horizon3,'
    assert extract_markers(text) == ['onyx_7', 'horizon3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$vertex6 should be ignored; keep ($vertex6) and skip $xxx.'
    assert extract_markers(text) == ['vertex6']


def test_preserves_order() -> None:
    text = 'Noise ($iris_2) plus $onyx_7. trailing $iris_2,'
    assert extract_markers(text) == ['iris_2', 'onyx_7']
