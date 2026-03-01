from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REQUIRED_TASK_FIELDS = {
    "task_id",
    "title",
    "category",
    "difficulty",
    "split",
    "quick",
    "path",
}

REQUIRED_TASK_FILES = [
    "prompt.md",
    "src/__init__.py",
    "tests/test_solution.py",
]
SCHEMA_FILE = "metadata.schema.json"


def _json_type_ok(value: Any, expected: str) -> bool:
    mapping: dict[str, tuple[type[Any], ...]] = {
        "object": (dict,),
        "array": (list,),
        "string": (str,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
    }
    if expected not in mapping:
        return True
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, mapping[expected])


def _validate_schema_node(
    *,
    value: Any,
    schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    expected_type = schema.get("type")
    if isinstance(expected_type, str) and not _json_type_ok(value, expected_type):
        errors.append(f"{path}: expected type `{expected_type}`")
        return

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant value `{schema['const']}`")

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        errors.append(f"{path}: value `{value}` not in enum {enum_values}")

    pattern = schema.get("pattern")
    if isinstance(pattern, str) and isinstance(value, str):
        if re.fullmatch(pattern, value) is None:
            errors.append(f"{path}: value `{value}` does not match pattern `{pattern}`")

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            missing = [key for key in required if key not in value]
            for key in missing:
                errors.append(f"{path}: missing required key `{key}`")

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, child_schema in properties.items():
                if key not in value:
                    continue
                if isinstance(child_schema, dict):
                    _validate_schema_node(
                        value=value[key],
                        schema=child_schema,
                        path=f"{path}.{key}",
                        errors=errors,
                    )

        if schema.get("additionalProperties") is False and isinstance(properties, dict):
            allowed = set(properties)
            extras = sorted(set(value) - allowed)
            for key in extras:
                errors.append(f"{path}: unexpected key `{key}`")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path}: expected at least {min_items} entries")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(f"{path}: expected at most {max_items} entries")

        if bool(schema.get("uniqueItems")) and len(value) != len(set(map(str, value))):
            errors.append(f"{path}: expected unique entries")

        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for idx, item in enumerate(value):
                _validate_schema_node(
                    value=item,
                    schema=items_schema,
                    path=f"{path}[{idx}]",
                    errors=errors,
                )


def validate_task_pack() -> tuple[bool, list[str]]:
    errors: list[str] = []
    root = Path(__file__).resolve().parent
    metadata_path = root / "metadata.json"
    schema_path = root / SCHEMA_FILE

    if not metadata_path.exists():
        return False, [f"Missing metadata file: {metadata_path}"]
    if not schema_path.exists():
        return False, [f"Missing metadata schema file: {schema_path}"]

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    if not isinstance(schema, dict):
        return False, [f"{schema_path} must be a JSON object"]
    _validate_schema_node(value=payload, schema=schema, path="metadata", errors=errors)

    required_top = {"pack_name", "pack_version", "counts", "categories", "tasks"}
    missing_top = sorted(required_top - set(payload))
    if missing_top:
        errors.append(f"metadata.json missing top-level key(s): {', '.join(missing_top)}")
        return False, errors

    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("metadata.json: `tasks` must be a list")
        return False, errors

    seen_ids: set[str] = set()
    split_counts = {"train": 0, "dev": 0, "test": 0}

    for idx, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"tasks[{idx}] must be an object")
            continue

        missing_fields = sorted(REQUIRED_TASK_FIELDS - set(task))
        if missing_fields:
            errors.append(f"tasks[{idx}] missing field(s): {', '.join(missing_fields)}")
            continue

        task_id = str(task["task_id"])
        if task_id in seen_ids:
            errors.append(f"Duplicate task_id: {task_id}")
        seen_ids.add(task_id)

        split = str(task["split"])
        if split not in split_counts:
            errors.append(f"Invalid split for {task_id}: {split}")
        else:
            split_counts[split] += 1

        rel_path = str(task["path"])
        task_dir = (root / rel_path).resolve()
        if not task_dir.exists():
            errors.append(f"Task path missing for {task_id}: {task_dir}")
            continue

        for rel in REQUIRED_TASK_FILES:
            file_path = task_dir / rel
            if not file_path.exists():
                errors.append(f"Missing task file for {task_id}: {file_path}")

        src_dir = task_dir / "src"
        if src_dir.exists():
            implementation_files = [
                path for path in src_dir.glob("*.py") if path.name != "__init__.py"
            ]
            if not implementation_files:
                errors.append(
                    f"Task {task_id} has no implementation modules in {src_dir} "
                    "(expected at least one .py file besides __init__.py)."
                )

    expected_total = 300
    if len(tasks) != expected_total:
        errors.append(f"Expected {expected_total} tasks, found {len(tasks)}")

    if split_counts != {"train": 200, "dev": 50, "test": 50}:
        errors.append(f"Unexpected split counts: {split_counts}")

    quick_count = sum(1 for task in tasks if isinstance(task, dict) and bool(task.get("quick")))
    if quick_count != 18:
        errors.append(f"Expected quick count 18, found {quick_count}")

    ok = not errors
    return ok, errors


def main() -> None:
    ok, errors = validate_task_pack()
    if ok:
        print("task_pack_v1 validation passed")
        return

    print("task_pack_v1 validation failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
