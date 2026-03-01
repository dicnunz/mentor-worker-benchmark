import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n apricot , 8 , utopia \\n temple , 3 , prairie \\n apricot , 2 , frost \\n temple , oops , utopia \\n utopia , 9 , utopia \\n  , 4 , prairie \\n temple , 7 , prairie \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'apricot': {'total': 10, 'count': 2, 'categories': ['frost', 'utopia']}, 'temple': {'total': 10, 'count': 2, 'categories': ['prairie']}, 'utopia': {'total': 9, 'count': 1, 'categories': ['utopia']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
