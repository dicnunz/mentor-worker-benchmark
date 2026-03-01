from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('island', 5), ('galaxy', 2), ('island', 1), ('meadow', 9), ('galaxy', -1), ('canyon', 0), ('charlie', -4)]
    assert rank_products(records, 3) == ['meadow', 'island', 'galaxy']


def test_tie_breaks_alphabetically() -> None:
    records = [('island', 4), ('canyon', 4), ('charlie', 4), ('island', -1), ('canyon', -1), ('galaxy', 1)]
    assert rank_products(records, 2) == ['charlie', 'canyon']


def test_non_positive_k_returns_empty() -> None:
    records = [('island', 5), ('galaxy', 2), ('island', 1), ('meadow', 9), ('galaxy', -1), ('canyon', 0), ('charlie', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
