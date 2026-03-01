from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ultra', 6), ('saffron', 2), ('ultra', 1), ('vivid', 10), ('saffron', -1), ('legend', 0), ('unity', -4)]
    assert rank_products(records, 3) == ['vivid', 'ultra', 'saffron']


def test_tie_breaks_alphabetically() -> None:
    records = [('ultra', 4), ('legend', 4), ('unity', 4), ('ultra', -1), ('legend', -1), ('saffron', 1)]
    assert rank_products(records, 2) == ['unity', 'legend']


def test_non_positive_k_returns_empty() -> None:
    records = [('ultra', 6), ('saffron', 2), ('ultra', 1), ('vivid', 10), ('saffron', -1), ('legend', 0), ('unity', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
