from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('pearl', 5), ('xpress', 2), ('pearl', 1), ('vivid', 10), ('xpress', -1), ('timber', 0), ('umber', -4)]
    assert rank_products(records, 3) == ['vivid', 'pearl', 'xpress']


def test_tie_breaks_alphabetically() -> None:
    records = [('pearl', 4), ('timber', 4), ('umber', 4), ('pearl', -1), ('timber', -1), ('xpress', 1)]
    assert rank_products(records, 2) == ['umber', 'pearl']


def test_non_positive_k_returns_empty() -> None:
    records = [('pearl', 5), ('xpress', 2), ('pearl', 1), ('vivid', 10), ('xpress', -1), ('timber', 0), ('umber', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
