from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %hazel_8 then %ultra4! repeat %HAZEL_8 and punctuation %ultra4,'
    assert extract_markers(text) == ['hazel_8', 'ultra4']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%feather0 should be ignored; keep (%feather0) and skip %x.'
    assert extract_markers(text) == ['feather0']


def test_preserves_order() -> None:
    text = 'Noise (%dynamo_3) plus %hazel_8. trailing %dynamo_3,'
    assert extract_markers(text) == ['dynamo_3', 'hazel_8']
