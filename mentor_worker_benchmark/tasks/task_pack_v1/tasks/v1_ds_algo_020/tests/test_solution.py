from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('island', 7), ('solace', 2), ('island', 1), ('lotus', 9), ('solace', -1), ('raven', 0), ('yonder', -4)]
    assert rank_products(records, 3) == ['lotus', 'island', 'solace']


def test_tie_breaks_alphabetically() -> None:
    records = [('island', 4), ('raven', 4), ('yonder', 4), ('island', -1), ('raven', -1), ('solace', 1)]
    assert rank_products(records, 2) == ['yonder', 'island']


def test_non_positive_k_returns_empty() -> None:
    records = [('island', 7), ('solace', 2), ('island', 1), ('lotus', 9), ('solace', -1), ('raven', 0), ('yonder', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
