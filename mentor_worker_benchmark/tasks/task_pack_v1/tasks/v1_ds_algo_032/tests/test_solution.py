from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('frost', 7), ('unity', 2), ('frost', 1), ('lima', 9), ('unity', -1), ('vertex', 0), ('iris', -4)]
    assert rank_products(records, 3) == ['lima', 'frost', 'unity']


def test_tie_breaks_alphabetically() -> None:
    records = [('frost', 4), ('vertex', 4), ('iris', 4), ('frost', -1), ('vertex', -1), ('unity', 1)]
    assert rank_products(records, 2) == ['iris', 'frost']


def test_non_positive_k_returns_empty() -> None:
    records = [('frost', 7), ('unity', 2), ('frost', 1), ('lima', 9), ('unity', -1), ('vertex', 0), ('iris', -4)]
    assert rank_products(records, 0) == []
