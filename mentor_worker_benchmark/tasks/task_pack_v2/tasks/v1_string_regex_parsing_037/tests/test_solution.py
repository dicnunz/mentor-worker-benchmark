from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $kepler_7 then $zebra2! repeat $KEPLER_7 and punctuation $zebra2,'
    assert extract_markers(text) == ['kepler_7', 'zebra2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$cinder5 should be ignored; keep ($cinder5) and skip $xx.'
    assert extract_markers(text) == ['cinder5']


def test_preserves_order() -> None:
    text = 'Noise ($pearl_2) plus $kepler_7. trailing $pearl_2,'
    assert extract_markers(text) == ['pearl_2', 'kepler_7']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
