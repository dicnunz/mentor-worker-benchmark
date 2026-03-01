import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n lotus , 6 , vertex \\n quest , 3 , kilo \\n lotus , 2 , kernel \\n quest , oops , vertex \\n canyon , 9 , vertex \\n  , 4 , kilo \\n quest , 7 , kilo \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'canyon': {'total': 9, 'count': 1, 'categories': ['vertex']}, 'lotus': {'total': 8, 'count': 2, 'categories': ['kernel', 'vertex']}, 'quest': {'total': 10, 'count': 2, 'categories': ['kilo']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
