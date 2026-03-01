from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #oasis_6 then #warden4! repeat #OASIS_6 and punctuation #warden4,'
    assert extract_markers(text) == ['oasis_6', 'warden4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#raven0 should be ignored; keep (#raven0) and skip #xx.'
    assert extract_markers(text) == ['raven0']


def test_preserves_order() -> None:
    text = 'Noise (#umber_1) plus #oasis_6. trailing #umber_1,'
    assert extract_markers(text) == ['umber_1', 'oasis_6']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
