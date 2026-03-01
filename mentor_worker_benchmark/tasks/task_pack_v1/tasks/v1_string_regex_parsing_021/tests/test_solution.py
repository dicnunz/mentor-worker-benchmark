from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #jade_1 then #nova0! repeat #JADE_1 and punctuation #nova0,'
    assert extract_markers(text) == ['jade_1', 'nova0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#delta3 should be ignored; keep (#delta3) and skip #x.'
    assert extract_markers(text) == ['delta3']


def test_preserves_order() -> None:
    text = 'Noise (#xylem_6) plus #jade_1. trailing #xylem_6,'
    assert extract_markers(text) == ['xylem_6', 'jade_1']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
