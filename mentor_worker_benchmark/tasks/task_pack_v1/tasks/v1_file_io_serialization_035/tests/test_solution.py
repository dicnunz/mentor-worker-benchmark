import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n kepler , 8 , jungle \\n xenon , 3 , meadow \\n kepler , 2 , dawn \\n xenon , oops , jungle \\n harbor , 9 , jungle \\n  , 4 , meadow \\n xenon , 7 , meadow \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'harbor': {'total': 9, 'count': 1, 'categories': ['jungle']}, 'kepler': {'total': 10, 'count': 2, 'categories': ['dawn', 'jungle']}, 'xenon': {'total': 10, 'count': 2, 'categories': ['meadow']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
