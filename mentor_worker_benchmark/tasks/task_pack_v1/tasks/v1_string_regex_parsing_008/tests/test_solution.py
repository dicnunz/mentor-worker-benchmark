from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %vertex_8 then %juliet1! repeat %VERTEX_8 and punctuation %juliet1,'
    assert extract_markers(text) == ['vertex_8', 'juliet1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%jungle4 should be ignored; keep (%jungle4) and skip %xxx.'
    assert extract_markers(text) == ['jungle4']


def test_preserves_order() -> None:
    text = 'Noise (%prairie_3) plus %vertex_8. trailing %prairie_3,'
    assert extract_markers(text) == ['prairie_3', 'vertex_8']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
