from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('warden', 5), ('grove', 2), ('warden', 1), ('drift', 10), ('grove', -1), ('xenon', 0), ('mercury', -4)]
    assert rank_products(records, 3) == ['drift', 'warden', 'grove']


def test_tie_breaks_alphabetically() -> None:
    records = [('warden', 4), ('xenon', 4), ('mercury', 4), ('warden', -1), ('xenon', -1), ('grove', 1)]
    assert rank_products(records, 2) == ['mercury', 'warden']


def test_non_positive_k_returns_empty() -> None:
    records = [('warden', 5), ('grove', 2), ('warden', 1), ('drift', 10), ('grove', -1), ('xenon', 0), ('mercury', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
