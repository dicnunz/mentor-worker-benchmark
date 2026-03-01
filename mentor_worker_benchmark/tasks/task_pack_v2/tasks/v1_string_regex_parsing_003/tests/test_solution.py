from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %xenon_3 then %oasis3! repeat %XENON_3 and punctuation %oasis3,'
    assert extract_markers(text) == ['xenon_3', 'oasis3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%prairie6 should be ignored; keep (%prairie6) and skip %x.'
    assert extract_markers(text) == ['prairie6']


def test_preserves_order() -> None:
    text = 'Noise (%opal_8) plus %xenon_3. trailing %opal_8,'
    assert extract_markers(text) == ['opal_8', 'xenon_3']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
