from __future__ import annotations

import json
from pathlib import Path

from mentor_worker_benchmark.tasks.task_pack_validation import validate_task_pack_payload

SCHEMA_FILE = "metadata.schema.json"


def validate_task_pack() -> tuple[bool, list[str]]:
    root = Path(__file__).resolve().parent
    metadata_path = root / "metadata.json"
    schema_path = root / SCHEMA_FILE

    if not metadata_path.exists():
        return False, [f"Missing metadata file: {metadata_path}"]
    if not schema_path.exists():
        return False, [f"Missing metadata schema file: {schema_path}"]

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return validate_task_pack_payload(root=root, payload=payload, schema=schema)


def main() -> None:
    ok, errors = validate_task_pack()
    if ok:
        print("task_pack_v2 validation passed")
        return

    print("task_pack_v2 validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
