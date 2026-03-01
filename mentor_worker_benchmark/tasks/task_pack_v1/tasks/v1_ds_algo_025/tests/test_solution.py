from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('charlie', 6), ('knight', 2), ('charlie', 1), ('nova', 10), ('knight', -1), ('zebra', 0), ('nectar', -4)]
    assert rank_products(records, 3) == ['nova', 'charlie', 'knight']


def test_tie_breaks_alphabetically() -> None:
    records = [('charlie', 4), ('zebra', 4), ('nectar', 4), ('charlie', -1), ('zebra', -1), ('knight', 1)]
    assert rank_products(records, 2) == ['nectar', 'charlie']


def test_non_positive_k_returns_empty() -> None:
    records = [('charlie', 6), ('knight', 2), ('charlie', 1), ('nova', 10), ('knight', -1), ('zebra', 0), ('nectar', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
