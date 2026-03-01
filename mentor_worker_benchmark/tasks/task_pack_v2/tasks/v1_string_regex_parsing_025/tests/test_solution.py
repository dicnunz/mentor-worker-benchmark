from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @nectarine_5 then @jade4! repeat @NECTARINE_5 and punctuation @jade4,'
    assert extract_markers(text) == ['nectarine_5', 'jade4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@saffron0 should be ignored; keep (@saffron0) and skip @xx.'
    assert extract_markers(text) == ['saffron0']


def test_preserves_order() -> None:
    text = 'Noise (@iris_0) plus @nectarine_5. trailing @iris_0,'
    assert extract_markers(text) == ['iris_0', 'nectarine_5']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
