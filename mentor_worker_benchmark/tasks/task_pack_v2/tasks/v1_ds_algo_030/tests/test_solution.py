from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('jade', 5), ('legend', 2), ('jade', 1), ('tango', 9), ('legend', -1), ('lima', 0), ('quartz', -4)]
    assert rank_products(records, 3) == ['tango', 'jade', 'legend']


def test_tie_breaks_alphabetically() -> None:
    records = [('jade', 4), ('lima', 4), ('quartz', 4), ('jade', -1), ('lima', -1), ('legend', 1)]
    assert rank_products(records, 2) == ['quartz', 'jade']


def test_non_positive_k_returns_empty() -> None:
    records = [('jade', 5), ('legend', 2), ('jade', 1), ('tango', 9), ('legend', -1), ('lima', 0), ('quartz', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
