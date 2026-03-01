from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %kernel_3 then %nebula5! repeat %KERNEL_3 and punctuation %nebula5,'
    assert extract_markers(text) == ['kernel_3', 'nebula5']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%ember1 should be ignored; keep (%ember1) and skip %x.'
    assert extract_markers(text) == ['ember1']


def test_preserves_order() -> None:
    text = 'Noise (%dawn_8) plus %kernel_3. trailing %dawn_8,'
    assert extract_markers(text) == ['dawn_8', 'kernel_3']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
