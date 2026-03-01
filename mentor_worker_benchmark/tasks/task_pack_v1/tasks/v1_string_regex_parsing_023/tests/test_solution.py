from src.solution import extract_markers


def test_normalizes_and_dedupes() -> None:
    text = 'Kickoff %elm_3 then %oasis2! repeat %ELM_3 and punctuation %oasis2,'
    assert extract_markers(text) == ['elm_3', 'oasis2']


def test_ignores_embedded_and_too_short_tokens() -> None:
    text = 'embedded%nectar5 should be ignored; keep (%nectar5) and skip %xxx.'
    assert extract_markers(text) == ['nectar5']


def test_preserves_order() -> None:
    text = 'Noise (%zen_8) plus %elm_3. trailing %zen_8,'
    assert extract_markers(text) == ['zen_8', 'elm_3']
