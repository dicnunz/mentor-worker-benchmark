from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('lima', 6), ('galaxy', 2), ('lima', 1), ('zenith', 9), ('galaxy', -1), ('lantern', 0), ('ultra', -4)]
    assert rank_products(records, 3) == ['zenith', 'lima', 'galaxy']


def test_tie_breaks_alphabetically() -> None:
    records = [('lima', 4), ('lantern', 4), ('ultra', 4), ('lima', -1), ('lantern', -1), ('galaxy', 1)]
    assert rank_products(records, 2) == ['ultra', 'lantern']


def test_non_positive_k_returns_empty() -> None:
    records = [('lima', 6), ('galaxy', 2), ('lima', 1), ('zenith', 9), ('galaxy', -1), ('lantern', 0), ('ultra', -4)]
    assert rank_products(records, 0) == []
