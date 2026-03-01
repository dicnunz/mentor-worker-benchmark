from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %quiver_3 then %pioneer6! repeat %QUIVER_3 and punctuation %pioneer6,'
    assert extract_markers(text) == ['quiver_3', 'pioneer6']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%temple2 should be ignored; keep (%temple2) and skip %xx.'
    assert extract_markers(text) == ['temple2']


def test_preserves_order() -> None:
    text = 'Noise (%legend_8) plus %quiver_3. trailing %legend_8,'
    assert extract_markers(text) == ['legend_8', 'quiver_3']
