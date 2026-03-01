from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('beacon', 6), ('mercury', 2), ('beacon', 1), ('prairie', 9), ('mercury', -1), ('raven', 0), ('jungle', -4)]
    assert rank_products(records, 3) == ['prairie', 'beacon', 'mercury']


def test_tie_breaks_alphabetically() -> None:
    records = [('beacon', 4), ('raven', 4), ('jungle', 4), ('beacon', -1), ('raven', -1), ('mercury', 1)]
    assert rank_products(records, 2) == ['jungle', 'beacon']


def test_non_positive_k_returns_empty() -> None:
    records = [('beacon', 6), ('mercury', 2), ('beacon', 1), ('prairie', 9), ('mercury', -1), ('raven', 0), ('jungle', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
