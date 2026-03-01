from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @knight_0 then @nectarine0! repeat @KNIGHT_0 and punctuation @nectarine0,'
    assert extract_markers(text) == ['knight_0', 'nectarine0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@zephyr3 should be ignored; keep (@zephyr3) and skip @x.'
    assert extract_markers(text) == ['zephyr3']


def test_preserves_order() -> None:
    text = 'Noise (@quartz_5) plus @knight_0. trailing @quartz_5,'
    assert extract_markers(text) == ['quartz_5', 'knight_0']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
