import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n alpha , 7 , orion \\n grove , 3 , yearling \\n alpha , 2 , zephyr \\n grove , oops , orion \\n saffron , 9 , orion \\n  , 4 , yearling \\n grove , 7 , yearling \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'alpha': {'total': 9, 'count': 2, 'categories': ['orion', 'zephyr']}, 'grove': {'total': 10, 'count': 2, 'categories': ['yearling']}, 'saffron': {'total': 9, 'count': 1, 'categories': ['orion']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
