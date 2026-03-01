import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n pioneer , 7 , acorn \\n quest , 3 , glider \\n pioneer , 2 , opal \\n quest , oops , acorn \\n meadow , 9 , acorn \\n  , 4 , glider \\n quest , 7 , glider \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'meadow': {'total': 9, 'count': 1, 'categories': ['acorn']}, 'pioneer': {'total': 9, 'count': 2, 'categories': ['acorn', 'opal']}, 'quest': {'total': 10, 'count': 2, 'categories': ['glider']}}
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
