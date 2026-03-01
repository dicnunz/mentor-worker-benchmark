import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n sierra , 7 , rocket \\n jungle , 3 , kilo \\n sierra , 2 , harbor \\n jungle , oops , rocket \\n fable , 9 , rocket \\n  , 4 , kilo \\n jungle , 7 , kilo \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'fable': {'total': 9, 'count': 1, 'categories': ['rocket']}, 'jungle': {'total': 10, 'count': 2, 'categories': ['kilo']}, 'sierra': {'total': 9, 'count': 2, 'categories': ['harbor', 'rocket']}}
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
