from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $prairie_7 then $grove6! repeat $PRAIRIE_7 and punctuation $grove6,'
    assert extract_markers(text) == ['prairie_7', 'grove6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$charlie2 should be ignored; keep ($charlie2) and skip $x.'
    assert extract_markers(text) == ['charlie2']


def test_preserves_order() -> None:
    text = 'Noise ($lima_2) plus $prairie_7. trailing $lima_2,'
    assert extract_markers(text) == ['lima_2', 'prairie_7']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
