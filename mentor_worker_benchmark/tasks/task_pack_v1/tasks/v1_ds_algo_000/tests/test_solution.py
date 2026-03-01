from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('quest', 5), ('prairie', 2), ('quest', 1), ('willow', 9), ('prairie', -1), ('breeze', 0), ('bravo', -4)]
    assert rank_products(records, 3) == ['willow', 'quest', 'prairie']


def test_tie_breaks_alphabetically() -> None:
    records = [('quest', 4), ('breeze', 4), ('bravo', 4), ('quest', -1), ('breeze', -1), ('prairie', 1)]
    assert rank_products(records, 2) == ['bravo', 'breeze']


def test_non_positive_k_returns_empty() -> None:
    records = [('quest', 5), ('prairie', 2), ('quest', 1), ('willow', 9), ('prairie', -1), ('breeze', 0), ('bravo', -4)]
    assert rank_products(records, 0) == []
