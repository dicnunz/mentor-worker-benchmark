from src.solution import rank_products


def test_aggregates_and_sorts() -> None:
    records = [('feather', 7), ('opal', 2), ('feather', 1), ('quartz', 9), ('opal', -1), ('legend', 0), ('delta', -4)]
    assert rank_products(records, 3) == ['quartz', 'feather', 'opal']


def test_tie_breaks_alphabetically() -> None:
    records = [('feather', 4), ('legend', 4), ('delta', 4), ('feather', -1), ('legend', -1), ('opal', 1)]
    assert rank_products(records, 2) == ['delta', 'feather']


def test_non_positive_k_returns_empty() -> None:
    records = [('feather', 7), ('opal', 2), ('feather', 1), ('quartz', 9), ('opal', -1), ('legend', 0), ('delta', -4)]
    assert rank_products(records, 0) == []
