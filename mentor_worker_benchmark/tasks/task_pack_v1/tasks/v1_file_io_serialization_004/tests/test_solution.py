import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n oasis , 5 , jungle \\n yonder , 3 , zephyr \\n oasis , 2 , temple \\n yonder , oops , jungle \\n apricot , 9 , jungle \\n  , 4 , zephyr \\n yonder , 7 , zephyr \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'apricot': {'total': 9, 'count': 1, 'categories': ['jungle']}, 'oasis': {'total': 7, 'count': 2, 'categories': ['jungle', 'temple']}, 'yonder': {'total': 10, 'count': 2, 'categories': ['zephyr']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
