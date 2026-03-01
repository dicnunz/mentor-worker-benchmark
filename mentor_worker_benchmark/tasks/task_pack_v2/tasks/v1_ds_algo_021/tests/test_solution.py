from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('delta', 5), ('whiskey', 2), ('delta', 1), ('knight', 10), ('whiskey', -1), ('mango', 0), ('xenon', -4)]
    assert rank_products(records, 3) == ['knight', 'delta', 'whiskey']


def test_tie_breaks_alphabetically() -> None:
    records = [('delta', 4), ('mango', 4), ('xenon', 4), ('delta', -1), ('mango', -1), ('whiskey', 1)]
    assert rank_products(records, 2) == ['xenon', 'delta']


def test_non_positive_k_returns_empty() -> None:
    records = [('delta', 5), ('whiskey', 2), ('delta', 1), ('knight', 10), ('whiskey', -1), ('mango', 0), ('xenon', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
