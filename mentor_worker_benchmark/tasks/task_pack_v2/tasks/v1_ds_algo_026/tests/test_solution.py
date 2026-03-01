from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('utopia', 7), ('wander', 2), ('utopia', 1), ('quill', 9), ('wander', -1), ('alpha', 0), ('yankee', -4)]
    assert rank_products(records, 3) == ['quill', 'utopia', 'wander']


def test_tie_breaks_alphabetically() -> None:
    records = [('utopia', 4), ('alpha', 4), ('yankee', 4), ('utopia', -1), ('alpha', -1), ('wander', 1)]
    assert rank_products(records, 2) == ['yankee', 'alpha']


def test_non_positive_k_returns_empty() -> None:
    records = [('utopia', 7), ('wander', 2), ('utopia', 1), ('quill', 9), ('wander', -1), ('alpha', 0), ('yankee', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
