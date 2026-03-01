from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('willow', 7), ('velvet', 2), ('willow', 1), ('yearling', 10), ('velvet', -1), ('feather', 0), ('timber', -4)]
    assert rank_products(records, 3) == ['yearling', 'willow', 'velvet']


def test_tie_breaks_alphabetically() -> None:
    records = [('willow', 4), ('feather', 4), ('timber', 4), ('willow', -1), ('feather', -1), ('velvet', 1)]
    assert rank_products(records, 2) == ['timber', 'feather']


def test_non_positive_k_returns_empty() -> None:
    records = [('willow', 7), ('velvet', 2), ('willow', 1), ('yearling', 10), ('velvet', -1), ('feather', 0), ('timber', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
