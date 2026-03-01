from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #saffron_6 then #quest2! repeat #SAFFRON_6 and punctuation #quest2,'
    assert extract_markers(text) == ['saffron_6', 'quest2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#quill5 should be ignored; keep (#quill5) and skip #xx.'
    assert extract_markers(text) == ['quill5']


def test_preserves_order() -> None:
    text = 'Noise (#ivory_1) plus #saffron_6. trailing #ivory_1,'
    assert extract_markers(text) == ['ivory_1', 'saffron_6']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
