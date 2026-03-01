from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('juliet', 5), ('opal', 2), ('juliet', 1), ('ivory', 10), ('opal', -1), ('rocket', 0), ('iris', -4)]
    assert rank_products(records, 3) == ['ivory', 'juliet', 'opal']


def test_tie_breaks_alphabetically() -> None:
    records = [('juliet', 4), ('rocket', 4), ('iris', 4), ('juliet', -1), ('rocket', -1), ('opal', 1)]
    assert rank_products(records, 2) == ['iris', 'juliet']


def test_non_positive_k_returns_empty() -> None:
    records = [('juliet', 5), ('opal', 2), ('juliet', 1), ('ivory', 10), ('opal', -1), ('rocket', 0), ('iris', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
