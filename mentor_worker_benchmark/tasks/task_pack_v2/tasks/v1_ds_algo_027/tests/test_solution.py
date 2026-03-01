from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('quartz', 5), ('nectar', 2), ('quartz', 1), ('kernel', 10), ('nectar', -1), ('blossom', 0), ('sierra', -4)]
    assert rank_products(records, 3) == ['kernel', 'quartz', 'nectar']


def test_tie_breaks_alphabetically() -> None:
    records = [('quartz', 4), ('blossom', 4), ('sierra', 4), ('quartz', -1), ('blossom', -1), ('nectar', 1)]
    assert rank_products(records, 2) == ['sierra', 'blossom']


def test_non_positive_k_returns_empty() -> None:
    records = [('quartz', 5), ('nectar', 2), ('quartz', 1), ('kernel', 10), ('nectar', -1), ('blossom', 0), ('sierra', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
