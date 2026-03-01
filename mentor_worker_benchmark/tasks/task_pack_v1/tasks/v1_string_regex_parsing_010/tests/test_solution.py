from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff @golf_0 then @dynamo3! repeat @GOLF_0 and punctuation @dynamo3,'
    assert extract_markers(text) == ['golf_0', 'dynamo3']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded@jade6 should be ignored; keep (@jade6) and skip @xx.'
    assert extract_markers(text) == ['jade6']


def test_preserves_order() -> None:
    text = 'Noise (@legend_5) plus @golf_0. trailing @legend_5,'
    assert extract_markers(text) == ['legend_5', 'golf_0']
