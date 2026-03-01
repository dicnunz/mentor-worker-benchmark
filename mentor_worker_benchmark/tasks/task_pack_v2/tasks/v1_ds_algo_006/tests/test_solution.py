from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('mango', 5), ('oasis', 2), ('mango', 1), ('wander', 9), ('oasis', -1), ('vertex', 0), ('frost', -4)]
    assert rank_products(records, 3) == ['wander', 'mango', 'oasis']


def test_tie_breaks_alphabetically() -> None:
    records = [('mango', 4), ('vertex', 4), ('frost', 4), ('mango', -1), ('vertex', -1), ('oasis', 1)]
    assert rank_products(records, 2) == ['frost', 'mango']


def test_non_positive_k_returns_empty() -> None:
    records = [('mango', 5), ('oasis', 2), ('mango', 1), ('wander', 9), ('oasis', -1), ('vertex', 0), ('frost', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
