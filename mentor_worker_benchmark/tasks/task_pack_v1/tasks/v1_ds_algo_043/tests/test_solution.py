from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ember', 6), ('grove', 2), ('ember', 1), ('opal', 10), ('grove', -1), ('charlie', 0), ('mango', -4)]
    assert rank_products(records, 3) == ['opal', 'ember', 'grove']


def test_tie_breaks_alphabetically() -> None:
    records = [('ember', 4), ('charlie', 4), ('mango', 4), ('ember', -1), ('charlie', -1), ('grove', 1)]
    assert rank_products(records, 2) == ['mango', 'charlie']


def test_non_positive_k_returns_empty() -> None:
    records = [('ember', 6), ('grove', 2), ('ember', 1), ('opal', 10), ('grove', -1), ('charlie', 0), ('mango', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
