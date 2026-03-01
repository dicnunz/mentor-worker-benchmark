from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('prairie', 6), ('xpress', 2), ('prairie', 1), ('amber', 9), ('xpress', -1), ('beacon', 0), ('nectarine', -4)]
    assert rank_products(records, 3) == ['amber', 'prairie', 'xpress']


def test_tie_breaks_alphabetically() -> None:
    records = [('prairie', 4), ('beacon', 4), ('nectarine', 4), ('prairie', -1), ('beacon', -1), ('xpress', 1)]
    assert rank_products(records, 2) == ['nectarine', 'beacon']


def test_non_positive_k_returns_empty() -> None:
    records = [('prairie', 6), ('xpress', 2), ('prairie', 1), ('amber', 9), ('xpress', -1), ('beacon', 0), ('nectarine', -4)]
    assert rank_products(records, 0) == []
