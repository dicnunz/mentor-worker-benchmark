from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $willow_2 then $beacon4! repeat $WILLOW_2 and punctuation $beacon4,'
    assert extract_markers(text) == ['willow_2', 'beacon4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$acorn0 should be ignored; keep ($acorn0) and skip $xxx.'
    assert extract_markers(text) == ['acorn0']


def test_preserves_order() -> None:
    text = 'Noise ($whiskey_7) plus $willow_2. trailing $whiskey_7,'
    assert extract_markers(text) == ['whiskey_7', 'willow_2']
