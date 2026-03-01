import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n jungle , 5 , warden \\n unity , 3 , maple \\n jungle , 2 , lantern \\n unity , oops , warden \\n willow , 9 , warden \\n  , 4 , maple \\n unity , 7 , maple \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'jungle': {'total': 7, 'count': 2, 'categories': ['lantern', 'warden']}, 'unity': {'total': 10, 'count': 2, 'categories': ['maple']}, 'willow': {'total': 9, 'count': 1, 'categories': ['warden']}}
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
