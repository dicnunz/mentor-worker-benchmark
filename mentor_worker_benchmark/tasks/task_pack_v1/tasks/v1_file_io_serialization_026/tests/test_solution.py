import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n jade , 7 , hazel \\n golf , 3 , saffron \\n jade , 2 , delta \\n golf , oops , hazel \\n meadow , 9 , hazel \\n  , 4 , saffron \\n golf , 7 , saffron \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'golf': {'total': 10, 'count': 2, 'categories': ['saffron']}, 'jade': {'total': 9, 'count': 2, 'categories': ['delta', 'hazel']}, 'meadow': {'total': 9, 'count': 1, 'categories': ['hazel']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
