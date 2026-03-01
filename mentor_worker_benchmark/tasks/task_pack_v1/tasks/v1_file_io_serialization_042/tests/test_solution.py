import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n temple , 7 , vivid \\n fable , 3 , voyage \\n temple , 2 , rocket \\n fable , oops , vivid \\n blossom , 9 , vivid \\n  , 4 , voyage \\n fable , 7 , voyage \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'blossom': {'total': 9, 'count': 1, 'categories': ['vivid']}, 'fable': {'total': 10, 'count': 2, 'categories': ['voyage']}, 'temple': {'total': 9, 'count': 2, 'categories': ['rocket', 'vivid']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
