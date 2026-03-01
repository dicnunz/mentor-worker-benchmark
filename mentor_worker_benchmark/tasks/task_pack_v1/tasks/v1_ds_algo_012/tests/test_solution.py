from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('quest', 5), ('legend', 2), ('quest', 1), ('nectar', 9), ('legend', -1), ('island', 0), ('whiskey', -4)]
    assert rank_products(records, 3) == ['nectar', 'quest', 'legend']


def test_tie_breaks_alphabetically() -> None:
    records = [('quest', 4), ('island', 4), ('whiskey', 4), ('quest', -1), ('island', -1), ('legend', 1)]
    assert rank_products(records, 2) == ['whiskey', 'island']


def test_non_positive_k_returns_empty() -> None:
    records = [('quest', 5), ('legend', 2), ('quest', 1), ('nectar', 9), ('legend', -1), ('island', 0), ('whiskey', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
