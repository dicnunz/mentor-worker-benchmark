from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('meadow', 7), ('whiskey', 2), ('meadow', 1), ('velvet', 10), ('whiskey', -1), ('river', 0), ('glider', -4)]
    assert rank_products(records, 3) == ['velvet', 'meadow', 'whiskey']


def test_tie_breaks_alphabetically() -> None:
    records = [('meadow', 4), ('river', 4), ('glider', 4), ('meadow', -1), ('river', -1), ('whiskey', 1)]
    assert rank_products(records, 2) == ['glider', 'meadow']


def test_non_positive_k_returns_empty() -> None:
    records = [('meadow', 7), ('whiskey', 2), ('meadow', 1), ('velvet', 10), ('whiskey', -1), ('river', 0), ('glider', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
