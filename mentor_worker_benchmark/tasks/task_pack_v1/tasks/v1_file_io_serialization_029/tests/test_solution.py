import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n ultra , 6 , golf \\n yankee , 3 , apricot \\n ultra , 2 , zebra \\n yankee , oops , golf \\n maple , 9 , golf \\n  , 4 , apricot \\n yankee , 7 , apricot \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'maple': {'total': 9, 'count': 1, 'categories': ['golf']}, 'ultra': {'total': 8, 'count': 2, 'categories': ['golf', 'zebra']}, 'yankee': {'total': 10, 'count': 2, 'categories': ['apricot']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
