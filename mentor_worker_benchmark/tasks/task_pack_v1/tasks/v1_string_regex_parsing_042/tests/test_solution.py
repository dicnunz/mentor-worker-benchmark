from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $sierra_2 then $dawn0! repeat $SIERRA_2 and punctuation $dawn0,'
    assert extract_markers(text) == ['sierra_2', 'dawn0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$frost3 should be ignored; keep ($frost3) and skip $x.'
    assert extract_markers(text) == ['frost3']


def test_preserves_order() -> None:
    text = 'Noise ($piper_7) plus $sierra_2. trailing $piper_7,'
    assert extract_markers(text) == ['piper_7', 'sierra_2']
