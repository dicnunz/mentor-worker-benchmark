from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('nectar', 7), ('dynamo', 2), ('nectar', 1), ('ripple', 10), ('dynamo', -1), ('foxtrot', 0), ('quest', -4)]
    assert rank_products(records, 3) == ['ripple', 'nectar', 'dynamo']


def test_tie_breaks_alphabetically() -> None:
    records = [('nectar', 4), ('foxtrot', 4), ('quest', 4), ('nectar', -1), ('foxtrot', -1), ('dynamo', 1)]
    assert rank_products(records, 2) == ['quest', 'foxtrot']


def test_non_positive_k_returns_empty() -> None:
    records = [('nectar', 7), ('dynamo', 2), ('nectar', 1), ('ripple', 10), ('dynamo', -1), ('foxtrot', 0), ('quest', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
