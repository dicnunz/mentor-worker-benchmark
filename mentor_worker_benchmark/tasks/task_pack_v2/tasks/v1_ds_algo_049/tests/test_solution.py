from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('xenon', 6), ('maple', 2), ('xenon', 1), ('utopia', 10), ('maple', -1), ('prairie', 0), ('nectarine', -4)]
    assert rank_products(records, 3) == ['utopia', 'xenon', 'maple']


def test_tie_breaks_alphabetically() -> None:
    records = [('xenon', 4), ('prairie', 4), ('nectarine', 4), ('xenon', -1), ('prairie', -1), ('maple', 1)]
    assert rank_products(records, 2) == ['nectarine', 'prairie']


def test_non_positive_k_returns_empty() -> None:
    records = [('xenon', 6), ('maple', 2), ('xenon', 1), ('utopia', 10), ('maple', -1), ('prairie', 0), ('nectarine', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
