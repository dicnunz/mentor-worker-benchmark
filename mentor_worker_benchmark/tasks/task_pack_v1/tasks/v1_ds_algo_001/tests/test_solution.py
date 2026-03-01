from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('dynamo', 6), ('whiskey', 2), ('dynamo', 1), ('ultra', 10), ('whiskey', -1), ('fable', 0), ('charlie', -4)]
    assert rank_products(records, 3) == ['ultra', 'dynamo', 'whiskey']


def test_tie_breaks_alphabetically() -> None:
    records = [('dynamo', 4), ('fable', 4), ('charlie', 4), ('dynamo', -1), ('fable', -1), ('whiskey', 1)]
    assert rank_products(records, 2) == ['charlie', 'dynamo']


def test_non_positive_k_returns_empty() -> None:
    records = [('dynamo', 6), ('whiskey', 2), ('dynamo', 1), ('ultra', 10), ('whiskey', -1), ('fable', 0), ('charlie', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
