import csv
import json


def summarize_transactions(input_csv: str, output_json: str) -> None:
    # Buggy starter: only keeps the first row and does not validate fields.
    with open(input_csv, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    result: dict[str, dict[str, object]] = {}
    if rows:
        first = rows[0]
        result[first["user"]] = {
            "total": int(first["amount"]),
            "count": 1,
            "categories": [first["category"]],
        }

    with open(output_json, "w", encoding="utf-8") as handle:
        json.dump(result, handle)
