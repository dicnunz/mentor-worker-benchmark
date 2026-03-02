from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [("yankee", 5), ("foxtrot", 2), ("yankee", 1), ("bravo", 10), ("foxtrot", -1)]
    assert rank_products(records, 2) == ["bravo", "yankee"]


def test_tie_breaks_alphabetically() -> None:
    records = [("yankee", 4), ("nebula", 4), ("golf", 4), ("yankee", -1), ("nebula", -1)]
    assert rank_products(records, 2) == ["golf", "nebula"]


def test_non_positive_k_returns_empty() -> None:
    records = [("yankee", 5), ("foxtrot", 2)]
    assert rank_products(records, 0) == []


def test_empty_records_returns_empty() -> None:
    assert rank_products([], 3) == []


def test_k_larger_than_population_is_safe() -> None:
    records = [("alpha", 2), ("beta", 1), ("alpha", -1)]
    assert rank_products(records, 10) == ["alpha", "beta"]


def test_filters_non_positive_totals() -> None:
    records = [("alpha", 2), ("beta", -1), ("beta", 1), ("gamma", 0)]
    assert rank_products(records, 5) == ["alpha"]
