import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n umber , 6 , acorn \\n timber , 3 , glider \\n umber , 2 , ember \\n timber , oops , acorn \\n yankee , 9 , acorn \\n  , 4 , glider \\n timber , 7 , glider \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'timber': {'total': 10, 'count': 2, 'categories': ['glider']}, 'umber': {'total': 8, 'count': 2, 'categories': ['acorn', 'ember']}, 'yankee': {'total': 9, 'count': 1, 'categories': ['acorn']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
