from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %breeze_3 then %knight1! repeat %BREEZE_3 and punctuation %knight1,'
    assert extract_markers(text) == ['breeze_3', 'knight1']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%ivory4 should be ignored; keep (%ivory4) and skip %xx.'
    assert extract_markers(text) == ['ivory4']


def test_preserves_order() -> None:
    text = 'Noise (%yankee_8) plus %breeze_3. trailing %yankee_8,'
    assert extract_markers(text) == ['yankee_8', 'breeze_3']
