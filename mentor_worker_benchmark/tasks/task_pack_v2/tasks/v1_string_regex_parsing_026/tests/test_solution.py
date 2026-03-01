from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff #umber_6 then #yonder5! repeat #UMBER_6 and punctuation #yonder5,'
    assert extract_markers(text) == ['umber_6', 'yonder5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded#ivory1 should be ignored; keep (#ivory1) and skip #xxx.'
    assert extract_markers(text) == ['ivory1']


def test_preserves_order() -> None:
    text = 'Noise (#kernel_1) plus #umber_6. trailing #kernel_1,'
    assert extract_markers(text) == ['kernel_1', 'umber_6']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
