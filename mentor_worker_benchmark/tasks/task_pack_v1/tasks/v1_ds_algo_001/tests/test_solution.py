from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('echo', 6), ('ultra', 2), ('echo', 1), ('legend', 10), ('ultra', -1), ('lantern', 0), ('grove', -4)]
    assert rank_products(records, 3) == ['legend', 'echo', 'ultra']


def test_tie_breaks_alphabetically() -> None:
    records = [('echo', 4), ('lantern', 4), ('grove', 4), ('echo', -1), ('lantern', -1), ('ultra', 1)]
    assert rank_products(records, 2) == ['grove', 'echo']


def test_non_positive_k_returns_empty() -> None:
    records = [('echo', 6), ('ultra', 2), ('echo', 1), ('legend', 10), ('ultra', -1), ('lantern', 0), ('grove', -4)]
    assert rank_products(records, 0) == []
