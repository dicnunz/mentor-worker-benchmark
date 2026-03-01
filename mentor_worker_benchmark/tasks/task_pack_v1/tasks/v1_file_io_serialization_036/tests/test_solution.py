import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n temple , 5 , timber \\n xylem , 3 , beacon \\n temple , 2 , mercury \\n xylem , oops , timber \\n beacon , 9 , timber \\n  , 4 , beacon \\n xylem , 7 , beacon \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'beacon': {'total': 9, 'count': 1, 'categories': ['timber']}, 'temple': {'total': 7, 'count': 2, 'categories': ['mercury', 'timber']}, 'xylem': {'total': 10, 'count': 2, 'categories': ['beacon']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}

def test_only_invalid_rows_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "invalid.csv"
    output_path = tmp_path / "invalid.json"
    input_path.write_text("user,amount,category\n name , bad , cat \n", encoding="utf-8")
    summarize_transactions(str(input_path), str(output_path))
    assert json.loads(output_path.read_text(encoding="utf-8")) == {}

def test_whitespace_only_user_rows_are_ignored(tmp_path) -> None:
    input_path = tmp_path / "spaces.csv"
    output_path = tmp_path / "spaces.json"
    input_path.write_text("user,amount,category\n   ,3,x\n", encoding="utf-8")
    summarize_transactions(str(input_path), str(output_path))
    assert json.loads(output_path.read_text(encoding="utf-8")) == {}
