from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $lima_7 then $timber0! repeat $LIMA_7 and punctuation $timber0,'
    assert extract_markers(text) == ['lima_7', 'timber0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$eagle3 should be ignored; keep ($eagle3) and skip $xx.'
    assert extract_markers(text) == ['eagle3']


def test_preserves_order() -> None:
    text = 'Noise ($willow_2) plus $lima_7. trailing $willow_2,'
    assert extract_markers(text) == ['willow_2', 'lima_7']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
