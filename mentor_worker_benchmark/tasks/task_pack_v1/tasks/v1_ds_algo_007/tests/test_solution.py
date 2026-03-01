from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('whiskey', 6), ('orion', 2), ('whiskey', 1), ('ultra', 10), ('orion', -1), ('echo', 0), ('vivid', -4)]
    assert rank_products(records, 3) == ['ultra', 'whiskey', 'orion']


def test_tie_breaks_alphabetically() -> None:
    records = [('whiskey', 4), ('echo', 4), ('vivid', 4), ('whiskey', -1), ('echo', -1), ('orion', 1)]
    assert rank_products(records, 2) == ['vivid', 'echo']


def test_non_positive_k_returns_empty() -> None:
    records = [('whiskey', 6), ('orion', 2), ('whiskey', 1), ('ultra', 10), ('orion', -1), ('echo', 0), ('vivid', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
