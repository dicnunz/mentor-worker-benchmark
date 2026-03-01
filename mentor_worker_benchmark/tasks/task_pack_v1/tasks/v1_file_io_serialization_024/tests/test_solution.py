import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n quartz , 5 , yearling \\n nova , 3 , galaxy \\n quartz , 2 , pearl \\n nova , oops , yearling \\n acorn , 9 , yearling \\n  , 4 , galaxy \\n nova , 7 , galaxy \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'acorn': {'total': 9, 'count': 1, 'categories': ['yearling']}, 'nova': {'total': 10, 'count': 2, 'categories': ['galaxy']}, 'quartz': {'total': 7, 'count': 2, 'categories': ['pearl', 'yearling']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
