from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ultra', 5), ('nectar', 2), ('ultra', 1), ('ember', 9), ('nectar', -1), ('onyx', 0), ('xpress', -4)]
    assert rank_products(records, 3) == ['ember', 'ultra', 'nectar']


def test_tie_breaks_alphabetically() -> None:
    records = [('ultra', 4), ('onyx', 4), ('xpress', 4), ('ultra', -1), ('onyx', -1), ('nectar', 1)]
    assert rank_products(records, 2) == ['xpress', 'onyx']


def test_non_positive_k_returns_empty() -> None:
    records = [('ultra', 5), ('nectar', 2), ('ultra', 1), ('ember', 9), ('nectar', -1), ('onyx', 0), ('xpress', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
