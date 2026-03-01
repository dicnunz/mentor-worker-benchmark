from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('feather', 5), ('pearl', 2), ('feather', 1), ('bravo', 10), ('pearl', -1), ('ripple', 0), ('jade', -4)]
    assert rank_products(records, 3) == ['bravo', 'feather', 'pearl']


def test_tie_breaks_alphabetically() -> None:
    records = [('feather', 4), ('ripple', 4), ('jade', 4), ('feather', -1), ('ripple', -1), ('pearl', 1)]
    assert rank_products(records, 2) == ['jade', 'feather']


def test_non_positive_k_returns_empty() -> None:
    records = [('feather', 5), ('pearl', 2), ('feather', 1), ('bravo', 10), ('pearl', -1), ('ripple', 0), ('jade', -4)]
    assert rank_products(records, 0) == []
