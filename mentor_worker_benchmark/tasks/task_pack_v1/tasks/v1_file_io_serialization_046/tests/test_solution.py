import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n jungle , 7 , charlie \\n lotus , 3 , solace \\n jungle , 2 , nectarine \\n lotus , oops , charlie \\n umber , 9 , charlie \\n  , 4 , solace \\n lotus , 7 , solace \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'jungle': {'total': 9, 'count': 2, 'categories': ['charlie', 'nectarine']}, 'lotus': {'total': 10, 'count': 2, 'categories': ['solace']}, 'umber': {'total': 9, 'count': 1, 'categories': ['charlie']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
