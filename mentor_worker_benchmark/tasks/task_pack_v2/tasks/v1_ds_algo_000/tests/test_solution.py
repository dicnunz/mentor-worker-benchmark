from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('sierra', 5), ('lantern', 2), ('sierra', 1), ('onyx', 9), ('lantern', -1), ('horizon', 0), ('timber', -4)]
    assert rank_products(records, 3) == ['onyx', 'sierra', 'lantern']


def test_tie_breaks_alphabetically() -> None:
    records = [('sierra', 4), ('horizon', 4), ('timber', 4), ('sierra', -1), ('horizon', -1), ('lantern', 1)]
    assert rank_products(records, 2) == ['timber', 'horizon']


def test_non_positive_k_returns_empty() -> None:
    records = [('sierra', 5), ('lantern', 2), ('sierra', 1), ('onyx', 9), ('lantern', -1), ('horizon', 0), ('timber', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
