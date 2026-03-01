from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('drift', 6), ('xenon', 2), ('drift', 1), ('willow', 9), ('xenon', -1), ('river', 0), ('voyage', -4)]
    assert rank_products(records, 3) == ['willow', 'drift', 'xenon']


def test_tie_breaks_alphabetically() -> None:
    records = [('drift', 4), ('river', 4), ('voyage', 4), ('drift', -1), ('river', -1), ('xenon', 1)]
    assert rank_products(records, 2) == ['voyage', 'drift']


def test_non_positive_k_returns_empty() -> None:
    records = [('drift', 6), ('xenon', 2), ('drift', 1), ('willow', 9), ('xenon', -1), ('river', 0), ('voyage', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
