from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('elm', 5), ('mango', 2), ('elm', 1), ('hazel', 9), ('mango', -1), ('xenon', 0), ('zen', -4)]
    assert rank_products(records, 3) == ['hazel', 'elm', 'mango']


def test_tie_breaks_alphabetically() -> None:
    records = [('elm', 4), ('xenon', 4), ('zen', 4), ('elm', -1), ('xenon', -1), ('mango', 1)]
    assert rank_products(records, 2) == ['zen', 'elm']


def test_non_positive_k_returns_empty() -> None:
    records = [('elm', 5), ('mango', 2), ('elm', 1), ('hazel', 9), ('mango', -1), ('xenon', 0), ('zen', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
