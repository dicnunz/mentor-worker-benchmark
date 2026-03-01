from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff $xylem_7 then $mango0! repeat $XYLEM_7 and punctuation $mango0,'
    assert extract_markers(text) == ['xylem_7', 'mango0']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded$foxtrot3 should be ignored; keep ($foxtrot3) and skip $xx.'
    assert extract_markers(text) == ['foxtrot3']


def test_preserves_order() -> None:
    text = 'Noise ($yonder_2) plus $xylem_7. trailing $yonder_2,'
    assert extract_markers(text) == ['yonder_2', 'xylem_7']
