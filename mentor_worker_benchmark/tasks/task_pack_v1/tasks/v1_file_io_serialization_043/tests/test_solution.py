import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n river , 8 , jungle \\n galaxy , 3 , amber \\n river , 2 , sunset \\n galaxy , oops , jungle \\n elm , 9 , jungle \\n  , 4 , amber \\n galaxy , 7 , amber \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'elm': {'total': 9, 'count': 1, 'categories': ['jungle']}, 'galaxy': {'total': 10, 'count': 2, 'categories': ['amber']}, 'river': {'total': 10, 'count': 2, 'categories': ['jungle', 'sunset']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
