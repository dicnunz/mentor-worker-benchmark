from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('sunset', 7), ('dynamo', 2), ('sunset', 1), ('apricot', 9), ('dynamo', -1), ('zephyr', 0), ('ultra', -4)]
    assert rank_products(records, 3) == ['apricot', 'sunset', 'dynamo']


def test_tie_breaks_alphabetically() -> None:
    records = [('sunset', 4), ('zephyr', 4), ('ultra', 4), ('sunset', -1), ('zephyr', -1), ('dynamo', 1)]
    assert rank_products(records, 2) == ['ultra', 'sunset']


def test_non_positive_k_returns_empty() -> None:
    records = [('sunset', 7), ('dynamo', 2), ('sunset', 1), ('apricot', 9), ('dynamo', -1), ('zephyr', 0), ('ultra', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
