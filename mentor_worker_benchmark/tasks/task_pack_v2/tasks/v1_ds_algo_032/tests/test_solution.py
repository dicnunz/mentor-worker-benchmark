from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('hotel', 7), ('thunder', 2), ('hotel', 1), ('piper', 9), ('thunder', -1), ('voyage', 0), ('legend', -4)]
    assert rank_products(records, 3) == ['piper', 'hotel', 'thunder']


def test_tie_breaks_alphabetically() -> None:
    records = [('hotel', 4), ('voyage', 4), ('legend', 4), ('hotel', -1), ('voyage', -1), ('thunder', 1)]
    assert rank_products(records, 2) == ['legend', 'hotel']


def test_non_positive_k_returns_empty() -> None:
    records = [('hotel', 7), ('thunder', 2), ('hotel', 1), ('piper', 9), ('thunder', -1), ('voyage', 0), ('legend', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
