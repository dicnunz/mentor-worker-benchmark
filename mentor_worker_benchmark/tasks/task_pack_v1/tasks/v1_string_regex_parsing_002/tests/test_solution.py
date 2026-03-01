from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $solace_2 then $prairie2! repeat $SOLACE_2 and punctuation $prairie2,'
    assert extract_markers(text) == ['solace_2', 'prairie2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$whiskey5 should be ignored; keep ($whiskey5) and skip $xxx.'
    assert extract_markers(text) == ['whiskey5']


def test_preserves_order() -> None:
    text = 'Noise ($vertex_7) plus $solace_2. trailing $vertex_7,'
    assert extract_markers(text) == ['vertex_7', 'solace_2']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
