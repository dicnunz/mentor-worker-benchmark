import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n nectar , 6 , frost \\n kernel , 3 , elm \\n nectar , 2 , xylem \\n kernel , oops , frost \\n frost , 9 , frost \\n  , 4 , elm \\n kernel , 7 , elm \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'frost': {'total': 9, 'count': 1, 'categories': ['frost']}, 'kernel': {'total': 10, 'count': 2, 'categories': ['elm']}, 'nectar': {'total': 8, 'count': 2, 'categories': ['frost', 'xylem']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
