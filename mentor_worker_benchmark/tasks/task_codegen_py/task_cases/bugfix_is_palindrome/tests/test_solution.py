from src.solution import is_palindrome


def test_ignores_case_and_spaces() -> None:
    assert is_palindrome("Never odd or even")


def test_ignores_punctuation() -> None:
    assert is_palindrome("A man, a plan, a canal: Panama!")


def test_detects_non_palindrome() -> None:
    assert not is_palindrome("Mentor benchmark")
