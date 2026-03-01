import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n yearling , 7 , amber \\n kepler , 3 , ember \\n yearling , 2 , fable \\n kepler , oops , amber \\n raven , 9 , amber \\n  , 4 , ember \\n kepler , 7 , ember \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'kepler': {'total': 10, 'count': 2, 'categories': ['ember']}, 'raven': {'total': 9, 'count': 1, 'categories': ['amber']}, 'yearling': {'total': 9, 'count': 2, 'categories': ['amber', 'fable']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
