import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n willow , 5 , island \\n alpha , 3 , nova \\n willow , 2 , whiskey \\n alpha , oops , island \\n grove , 9 , island \\n  , 4 , nova \\n alpha , 7 , nova \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'alpha': {'total': 10, 'count': 2, 'categories': ['nova']}, 'grove': {'total': 9, 'count': 1, 'categories': ['island']}, 'willow': {'total': 7, 'count': 2, 'categories': ['island', 'whiskey']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
