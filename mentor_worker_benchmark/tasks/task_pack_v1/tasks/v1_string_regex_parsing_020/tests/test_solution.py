from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @hotel_0 then @warden6! repeat @HOTEL_0 and punctuation @warden6,'
    assert extract_markers(text) == ['hotel_0', 'warden6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@yearling2 should be ignored; keep (@yearling2) and skip @xxx.'
    assert extract_markers(text) == ['yearling2']


def test_preserves_order() -> None:
    text = 'Noise (@willow_5) plus @hotel_0. trailing @willow_5,'
    assert extract_markers(text) == ['willow_5', 'hotel_0']

def test_empty_input_returns_empty_list() -> None:
    assert extract_markers("") == []

def test_no_marker_returns_empty_list() -> None:
    assert extract_markers("plain text without marker") == []
