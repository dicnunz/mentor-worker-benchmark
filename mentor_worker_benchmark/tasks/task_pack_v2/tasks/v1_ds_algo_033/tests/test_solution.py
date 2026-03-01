from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('sunset', 5), ('river', 2), ('sunset', 1), ('zen', 10), ('river', -1), ('rocket', 0), ('quartz', -4)]
    assert rank_products(records, 3) == ['zen', 'sunset', 'river']


def test_tie_breaks_alphabetically() -> None:
    records = [('sunset', 4), ('rocket', 4), ('quartz', 4), ('sunset', -1), ('rocket', -1), ('river', 1)]
    assert rank_products(records, 2) == ['quartz', 'rocket']


def test_non_positive_k_returns_empty() -> None:
    records = [('sunset', 5), ('river', 2), ('sunset', 1), ('zen', 10), ('river', -1), ('rocket', 0), ('quartz', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
