from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $whiskey_2 then $utopia5! repeat $WHISKEY_2 and punctuation $utopia5,'
    assert extract_markers(text) == ['whiskey_2', 'utopia5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$vivid1 should be ignored; keep ($vivid1) and skip $x.'
    assert extract_markers(text) == ['vivid1']


def test_preserves_order() -> None:
    text = 'Noise ($willow_7) plus $whiskey_2. trailing $willow_7,'
    assert extract_markers(text) == ['willow_7', 'whiskey_2']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
