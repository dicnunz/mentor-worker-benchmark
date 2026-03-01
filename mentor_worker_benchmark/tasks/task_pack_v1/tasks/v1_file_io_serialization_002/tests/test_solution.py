import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n raven , 7 , glider \\n ultra , 3 , cobalt \\n raven , 2 , temple \\n ultra , oops , glider \\n glider , 9 , glider \\n  , 4 , cobalt \\n ultra , 7 , cobalt \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'glider': {'total': 9, 'count': 1, 'categories': ['glider']}, 'raven': {'total': 9, 'count': 2, 'categories': ['glider', 'temple']}, 'ultra': {'total': 10, 'count': 2, 'categories': ['cobalt']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
