from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('piper', 6), ('yonder', 2), ('piper', 1), ('alpha', 9), ('yonder', -1), ('nectar', 0), ('quartz', -4)]
    assert rank_products(records, 3) == ['alpha', 'piper', 'yonder']


def test_tie_breaks_alphabetically() -> None:
    records = [('piper', 4), ('nectar', 4), ('quartz', 4), ('piper', -1), ('nectar', -1), ('yonder', 1)]
    assert rank_products(records, 2) == ['quartz', 'nectar']


def test_non_positive_k_returns_empty() -> None:
    records = [('piper', 6), ('yonder', 2), ('piper', 1), ('alpha', 9), ('yonder', -1), ('nectar', 0), ('quartz', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
