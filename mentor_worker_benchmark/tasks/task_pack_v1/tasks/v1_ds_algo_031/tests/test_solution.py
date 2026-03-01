from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('vertex', 6), ('blossom', 2), ('vertex', 1), ('orion', 10), ('blossom', -1), ('echo', 0), ('ivory', -4)]
    assert rank_products(records, 3) == ['orion', 'vertex', 'blossom']


def test_tie_breaks_alphabetically() -> None:
    records = [('vertex', 4), ('echo', 4), ('ivory', 4), ('vertex', -1), ('echo', -1), ('blossom', 1)]
    assert rank_products(records, 2) == ['ivory', 'echo']


def test_non_positive_k_returns_empty() -> None:
    records = [('vertex', 6), ('blossom', 2), ('vertex', 1), ('orion', 10), ('blossom', -1), ('echo', 0), ('ivory', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
