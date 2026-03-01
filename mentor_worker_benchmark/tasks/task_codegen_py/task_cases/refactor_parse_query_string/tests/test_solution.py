from src.solution import parse_query_string


def test_basic_single_values() -> None:
    assert parse_query_string("x=1&y=2") == {"x": "1", "y": "2"}


def test_repeated_keys_become_list() -> None:
    assert parse_query_string("a=1&a=2&a=3") == {"a": ["1", "2", "3"]}


def test_decoding_and_plus_space() -> None:
    assert parse_query_string("name=Jane+Doe&city=New%20York") == {
        "name": "Jane Doe",
        "city": "New York",
    }


def test_ignores_empty_segments() -> None:
    assert parse_query_string("&&x=1&&") == {"x": "1"}
