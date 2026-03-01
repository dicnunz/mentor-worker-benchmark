from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('kernel', 6), ('apricot', 2), ('kernel', 1), ('drift', 9), ('apricot', -1), ('solace', 0), ('mango', -4)]
    assert rank_products(records, 3) == ['drift', 'kernel', 'apricot']


def test_tie_breaks_alphabetically() -> None:
    records = [('kernel', 4), ('solace', 4), ('mango', 4), ('kernel', -1), ('solace', -1), ('apricot', 1)]
    assert rank_products(records, 2) == ['mango', 'kernel']


def test_non_positive_k_returns_empty() -> None:
    records = [('kernel', 6), ('apricot', 2), ('kernel', 1), ('drift', 9), ('apricot', -1), ('solace', 0), ('mango', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
