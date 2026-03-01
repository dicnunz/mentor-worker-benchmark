from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('nectar', 7), ('maple', 2), ('nectar', 1), ('glider', 9), ('maple', -1), ('kilo', 0), ('eagle', -4)]
    assert rank_products(records, 3) == ['glider', 'nectar', 'maple']


def test_tie_breaks_alphabetically() -> None:
    records = [('nectar', 4), ('kilo', 4), ('eagle', 4), ('nectar', -1), ('kilo', -1), ('maple', 1)]
    assert rank_products(records, 2) == ['eagle', 'kilo']


def test_non_positive_k_returns_empty() -> None:
    records = [('nectar', 7), ('maple', 2), ('nectar', 1), ('glider', 9), ('maple', -1), ('kilo', 0), ('eagle', -4)]
    assert rank_products(records, 0) == []
