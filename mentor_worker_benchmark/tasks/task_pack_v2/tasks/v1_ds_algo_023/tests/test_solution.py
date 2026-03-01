from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('acorn', 7), ('island', 2), ('acorn', 1), ('nectar', 10), ('island', -1), ('yonder', 0), ('kilo', -4)]
    assert rank_products(records, 3) == ['nectar', 'acorn', 'island']


def test_tie_breaks_alphabetically() -> None:
    records = [('acorn', 4), ('yonder', 4), ('kilo', 4), ('acorn', -1), ('yonder', -1), ('island', 1)]
    assert rank_products(records, 2) == ['kilo', 'acorn']


def test_non_positive_k_returns_empty() -> None:
    records = [('acorn', 7), ('island', 2), ('acorn', 1), ('nectar', 10), ('island', -1), ('yonder', 0), ('kilo', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
