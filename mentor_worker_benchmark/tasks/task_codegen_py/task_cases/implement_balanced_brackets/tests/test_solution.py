from src.solution import balanced_brackets


def test_balanced_nested() -> None:
    assert balanced_brackets("if (a[0] == '{') { return true; }")


def test_unbalanced_missing_closer() -> None:
    assert not balanced_brackets("([{}]")


def test_unbalanced_wrong_order() -> None:
    assert not balanced_brackets("(]")
