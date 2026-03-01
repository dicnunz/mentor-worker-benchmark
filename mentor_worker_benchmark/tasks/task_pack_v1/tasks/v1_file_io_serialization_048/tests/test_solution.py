import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n piper , 5 , velvet \\n eagle , 3 , dawn \\n piper , 2 , sierra \\n eagle , oops , velvet \\n prairie , 9 , velvet \\n  , 4 , dawn \\n eagle , 7 , dawn \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'eagle': {'total': 10, 'count': 2, 'categories': ['dawn']}, 'piper': {'total': 7, 'count': 2, 'categories': ['sierra', 'velvet']}, 'prairie': {'total': 9, 'count': 1, 'categories': ['velvet']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
