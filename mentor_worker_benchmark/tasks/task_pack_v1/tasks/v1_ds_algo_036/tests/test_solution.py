from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('knight', 5), ('delta', 2), ('knight', 1), ('sierra', 9), ('delta', -1), ('voyage', 0), ('xpress', -4)]
    assert rank_products(records, 3) == ['sierra', 'knight', 'delta']


def test_tie_breaks_alphabetically() -> None:
    records = [('knight', 4), ('voyage', 4), ('xpress', 4), ('knight', -1), ('voyage', -1), ('delta', 1)]
    assert rank_products(records, 2) == ['xpress', 'knight']


def test_non_positive_k_returns_empty() -> None:
    records = [('knight', 5), ('delta', 2), ('knight', 1), ('sierra', 9), ('delta', -1), ('voyage', 0), ('xpress', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
