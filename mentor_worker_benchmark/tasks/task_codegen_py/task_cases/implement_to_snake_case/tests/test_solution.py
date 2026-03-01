from src.solution import to_snake_case


def test_camel_case() -> None:
    assert to_snake_case("HTTPRequest") == "http_request"


def test_mixed_separators() -> None:
    assert to_snake_case("some-mixed stringValue") == "some_mixed_string_value"


def test_already_snake_case() -> None:
    assert to_snake_case("already_snake_2") == "already_snake_2"
