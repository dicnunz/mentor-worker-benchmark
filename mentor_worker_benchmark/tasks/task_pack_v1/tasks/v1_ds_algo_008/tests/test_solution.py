from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('delta', 7), ('hazel', 2), ('delta', 1), ('alpha', 9), ('hazel', -1), ('acorn', 0), ('jade', -4)]
    assert rank_products(records, 3) == ['alpha', 'delta', 'hazel']


def test_tie_breaks_alphabetically() -> None:
    records = [('delta', 4), ('acorn', 4), ('jade', 4), ('delta', -1), ('acorn', -1), ('hazel', 1)]
    assert rank_products(records, 2) == ['jade', 'acorn']


def test_non_positive_k_returns_empty() -> None:
    records = [('delta', 7), ('hazel', 2), ('delta', 1), ('alpha', 9), ('hazel', -1), ('acorn', 0), ('jade', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
