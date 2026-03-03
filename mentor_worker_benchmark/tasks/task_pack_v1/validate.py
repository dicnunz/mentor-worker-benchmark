from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.tasks.task_pack_validation import validate_task_pack_payload

SCHEMA_FILE = "metadata.schema.json"


def validate_task_pack(
    *,
    strict: bool = False,
    return_report: bool = False,
) -> tuple[bool, list[str]] | tuple[bool, list[str], dict[str, Any]]:
    root = Path(__file__).resolve().parent
    metadata_path = root / "metadata.json"
    schema_path = root / SCHEMA_FILE

    if not metadata_path.exists():
        base = (False, [f"Missing metadata file: {metadata_path}"])
        if return_report:
            return base[0], base[1], {
                "pack_name": "task_pack_v1",
                "strict": strict,
                "schema_errors": list(base[1]),
                "strength_gates": {"enabled": False, "reason": "metadata_missing"},
            }
        return base
    if not schema_path.exists():
        base = (False, [f"Missing metadata schema file: {schema_path}"])
        if return_report:
            return base[0], base[1], {
                "pack_name": "task_pack_v1",
                "strict": strict,
                "schema_errors": list(base[1]),
                "strength_gates": {"enabled": False, "reason": "schema_missing"},
            }
        return base

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return validate_task_pack_payload(
        root=root,
        payload=payload,
        schema=schema,
        strict=strict,
        return_report=return_report,
        allowlist_path=root / "strength_allowlist.json",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate task_pack_v1 metadata and test-strength gates.")
    parser.add_argument("--strict", action="store_true", help="Fail on strict test-strength gate policy.")
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write the JSON validation report.",
    )
    args = parser.parse_args()

    ok, errors, report = validate_task_pack(strict=args.strict, return_report=True)

    report_json = json.dumps(report, indent=2)
    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_json + "\n", encoding="utf-8")
    print(report_json)

    if ok:
        return

    if errors:
        print("task_pack_v1 validation failed:")
        for error in errors:
            print(f"- {error}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
