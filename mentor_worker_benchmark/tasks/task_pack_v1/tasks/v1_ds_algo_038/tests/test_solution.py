from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('xenon', 7), ('horizon', 2), ('xenon', 1), ('nectar', 9), ('horizon', -1), ('rocket', 0), ('orion', -4)]
    assert rank_products(records, 3) == ['nectar', 'xenon', 'horizon']


def test_tie_breaks_alphabetically() -> None:
    records = [('xenon', 4), ('rocket', 4), ('orion', 4), ('xenon', -1), ('rocket', -1), ('horizon', 1)]
    assert rank_products(records, 2) == ['orion', 'rocket']


def test_non_positive_k_returns_empty() -> None:
    records = [('xenon', 7), ('horizon', 2), ('xenon', 1), ('nectar', 9), ('horizon', -1), ('rocket', 0), ('orion', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
