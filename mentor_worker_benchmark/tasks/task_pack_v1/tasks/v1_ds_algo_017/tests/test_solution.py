from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('iris', 7), ('warden', 2), ('iris', 1), ('piper', 10), ('warden', -1), ('hazel', 0), ('jungle', -4)]
    assert rank_products(records, 3) == ['piper', 'iris', 'warden']


def test_tie_breaks_alphabetically() -> None:
    records = [('iris', 4), ('hazel', 4), ('jungle', 4), ('iris', -1), ('hazel', -1), ('warden', 1)]
    assert rank_products(records, 2) == ['jungle', 'hazel']


def test_non_positive_k_returns_empty() -> None:
    records = [('iris', 7), ('warden', 2), ('iris', 1), ('piper', 10), ('warden', -1), ('hazel', 0), ('jungle', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
