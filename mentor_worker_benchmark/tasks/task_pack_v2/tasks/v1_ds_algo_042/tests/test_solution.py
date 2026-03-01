from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('lantern', 5), ('horizon', 2), ('lantern', 1), ('yonder', 9), ('horizon', -1), ('timber', 0), ('saffron', -4)]
    assert rank_products(records, 3) == ['yonder', 'lantern', 'horizon']


def test_tie_breaks_alphabetically() -> None:
    records = [('lantern', 4), ('timber', 4), ('saffron', 4), ('lantern', -1), ('timber', -1), ('horizon', 1)]
    assert rank_products(records, 2) == ['saffron', 'lantern']


def test_non_positive_k_returns_empty() -> None:
    records = [('lantern', 5), ('horizon', 2), ('lantern', 1), ('yonder', 9), ('horizon', -1), ('timber', 0), ('saffron', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
