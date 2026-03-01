from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('ripple', 5), ('jade', 2), ('ripple', 1), ('xpress', 9), ('jade', -1), ('bravo', 0), ('willow', -4)]
    assert rank_products(records, 3) == ['xpress', 'ripple', 'jade']


def test_tie_breaks_alphabetically() -> None:
    records = [('ripple', 4), ('bravo', 4), ('willow', 4), ('ripple', -1), ('bravo', -1), ('jade', 1)]
    assert rank_products(records, 2) == ['willow', 'bravo']


def test_non_positive_k_returns_empty() -> None:
    records = [('ripple', 5), ('jade', 2), ('ripple', 1), ('xpress', 9), ('jade', -1), ('bravo', 0), ('willow', -4)]
    assert rank_products(records, 0) == []
