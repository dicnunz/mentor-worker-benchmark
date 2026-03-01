from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('apricot', 7), ('mercury', 2), ('apricot', 1), ('pearl', 9), ('mercury', -1), ('yankee', 0), ('nova', -4)]
    assert rank_products(records, 3) == ['pearl', 'apricot', 'mercury']


def test_tie_breaks_alphabetically() -> None:
    records = [('apricot', 4), ('yankee', 4), ('nova', 4), ('apricot', -1), ('yankee', -1), ('mercury', 1)]
    assert rank_products(records, 2) == ['nova', 'apricot']


def test_non_positive_k_returns_empty() -> None:
    records = [('apricot', 7), ('mercury', 2), ('apricot', 1), ('pearl', 9), ('mercury', -1), ('yankee', 0), ('nova', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
