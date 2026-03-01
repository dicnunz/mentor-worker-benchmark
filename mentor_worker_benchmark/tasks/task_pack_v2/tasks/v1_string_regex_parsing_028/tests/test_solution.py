from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %meadow_8 then %xenon0! repeat %MEADOW_8 and punctuation %xenon0,'
    assert extract_markers(text) == ['meadow_8', 'xenon0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%solace3 should be ignored; keep (%solace3) and skip %xx.'
    assert extract_markers(text) == ['solace3']


def test_preserves_order() -> None:
    text = 'Noise (%echo_3) plus %meadow_8. trailing %echo_3,'
    assert extract_markers(text) == ['echo_3', 'meadow_8']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
