from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('mercury', 7), ('sierra', 2), ('mercury', 1), ('raven', 9), ('sierra', -1), ('nebula', 0), ('onyx', -4)]
    assert rank_products(records, 3) == ['raven', 'mercury', 'sierra']


def test_tie_breaks_alphabetically() -> None:
    records = [('mercury', 4), ('nebula', 4), ('onyx', 4), ('mercury', -1), ('nebula', -1), ('sierra', 1)]
    assert rank_products(records, 2) == ['onyx', 'mercury']


def test_non_positive_k_returns_empty() -> None:
    records = [('mercury', 7), ('sierra', 2), ('mercury', 1), ('raven', 9), ('sierra', -1), ('nebula', 0), ('onyx', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
