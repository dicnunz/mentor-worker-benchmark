import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n yankee , 6 , pearl \\n ivory , 3 , zebra \\n yankee , 2 , solace \\n ivory , oops , pearl \\n hazel , 9 , pearl \\n  , 4 , zebra \\n ivory , 7 , zebra \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'hazel': {'total': 9, 'count': 1, 'categories': ['pearl']}, 'ivory': {'total': 10, 'count': 2, 'categories': ['zebra']}, 'yankee': {'total': 8, 'count': 2, 'categories': ['pearl', 'solace']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
