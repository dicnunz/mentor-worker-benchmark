from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('knight', 7), ('opal', 2), ('knight', 1), ('hazel', 10), ('opal', -1), ('charlie', 0), ('voyage', -4)]
    assert rank_products(records, 3) == ['hazel', 'knight', 'opal']


def test_tie_breaks_alphabetically() -> None:
    records = [('knight', 4), ('charlie', 4), ('voyage', 4), ('knight', -1), ('charlie', -1), ('opal', 1)]
    assert rank_products(records, 2) == ['voyage', 'charlie']


def test_non_positive_k_returns_empty() -> None:
    records = [('knight', 7), ('opal', 2), ('knight', 1), ('hazel', 10), ('opal', -1), ('charlie', 0), ('voyage', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
