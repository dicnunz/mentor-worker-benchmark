import json

from src.solution import summarize_transactions


def test_aggregates_valid_rows(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text('user,amount,category\\n harbor , 8 , sunset \\n thunder , 3 , blossom \\n harbor , 2 , vertex \\n thunder , oops , sunset \\n unity , 9 , sunset \\n  , 4 , blossom \\n thunder , 7 , blossom \\n', encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload == {'harbor': {'total': 10, 'count': 2, 'categories': ['sunset', 'vertex']}, 'thunder': {'total': 10, 'count': 2, 'categories': ['blossom']}, 'unity': {'total': 9, 'count': 1, 'categories': ['sunset']}}
    assert list(payload) == sorted(payload)


def test_empty_input_produces_empty_object(tmp_path) -> None:
    input_path = tmp_path / "in.csv"
    output_path = tmp_path / "out.json"
    input_path.write_text("user,amount,category\n", encoding="utf-8")

    summarize_transactions(str(input_path), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {}
