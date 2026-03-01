from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @elm_5 then @willow3! repeat @ELM_5 and punctuation @willow3,'
    assert extract_markers(text) == ['elm_5', 'willow3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@xpress6 should be ignored; keep (@xpress6) and skip @x.'
    assert extract_markers(text) == ['xpress6']


def test_preserves_order() -> None:
    text = 'Noise (@frost_0) plus @elm_5. trailing @frost_0,'
    assert extract_markers(text) == ['frost_0', 'elm_5']
