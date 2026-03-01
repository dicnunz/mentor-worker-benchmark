from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ripple', 6), ('timber', 2), ('ripple', 1), ('maple', 9), ('timber', -1), ('feather', 0), ('raven', -4)]
    assert rank_products(records, 3) == ['maple', 'ripple', 'timber']


def test_tie_breaks_alphabetically() -> None:
    records = [('ripple', 4), ('feather', 4), ('raven', 4), ('ripple', -1), ('feather', -1), ('timber', 1)]
    assert rank_products(records, 2) == ['raven', 'feather']


def test_non_positive_k_returns_empty() -> None:
    records = [('ripple', 6), ('timber', 2), ('ripple', 1), ('maple', 9), ('timber', -1), ('feather', 0), ('raven', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
