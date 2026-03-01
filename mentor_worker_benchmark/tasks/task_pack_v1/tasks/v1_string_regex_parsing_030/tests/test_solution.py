from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @cinder_0 then @quartz2! repeat @CINDER_0 and punctuation @quartz2,'
    assert extract_markers(text) == ['cinder_0', 'quartz2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@feather5 should be ignored; keep (@feather5) and skip @x.'
    assert extract_markers(text) == ['feather5']


def test_preserves_order() -> None:
    text = 'Noise (@onyx_5) plus @cinder_0. trailing @onyx_5,'
    assert extract_markers(text) == ['onyx_5', 'cinder_0']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
