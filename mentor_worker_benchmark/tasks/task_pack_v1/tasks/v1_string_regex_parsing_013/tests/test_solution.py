from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %feather_3 then %raven6! repeat %FEATHER_3 and punctuation %raven6,'
    assert extract_markers(text) == ['feather_3', 'raven6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%thunder2 should be ignored; keep (%thunder2) and skip %xx.'
    assert extract_markers(text) == ['thunder2']


def test_preserves_order() -> None:
    text = 'Noise (%quartz_8) plus %feather_3. trailing %quartz_8,'
    assert extract_markers(text) == ['quartz_8', 'feather_3']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
