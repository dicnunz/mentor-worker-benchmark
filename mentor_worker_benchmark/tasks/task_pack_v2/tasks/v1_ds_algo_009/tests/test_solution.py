from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('orion', 5), ('feather', 2), ('orion', 1), ('golf', 10), ('feather', -1), ('temple', 0), ('zenith', -4)]
    assert rank_products(records, 3) == ['golf', 'orion', 'feather']


def test_tie_breaks_alphabetically() -> None:
    records = [('orion', 4), ('temple', 4), ('zenith', 4), ('orion', -1), ('temple', -1), ('feather', 1)]
    assert rank_products(records, 2) == ['zenith', 'orion']


def test_non_positive_k_returns_empty() -> None:
    records = [('orion', 5), ('feather', 2), ('orion', 1), ('golf', 10), ('feather', -1), ('temple', 0), ('zenith', -4)]
    assert rank_products(records, 0) == []

def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []

def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
    assert rank_products(records, 10) == ["alpha", "beta"]
