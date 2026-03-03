from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from mentor_worker_benchmark.tasks.task_codegen_py.harness import run_pytest

REQUIRED_TOP_LEVEL_KEYS = {"pack_name", "pack_version", "counts", "categories", "tasks"}
REQUIRED_TASK_FIELDS = {
    "task_id",
    "title",
    "category",
    "difficulty",
    "split",
    "quick",
    "path",
}
DEFAULT_REQUIRED_TASK_FILES = [
    "prompt.md",
    "src/__init__.py",
    "tests/test_solution.py",
]

DEFAULT_MUTATION_TIMEOUT_SECONDS = 8
DEFAULT_MUTATION_SAMPLE_LIMIT = 80
EDGE_CASE_KEYWORDS = (
    "empty",
    "none",
    "null",
    "invalid",
    "error",
    "boundary",
    "edge",
    "zero",
    "negative",
    "missing",
    "whitespace",
    "overflow",
    "underflow",
    "nan",
)
NEGATIVE_TEST_PATTERNS = (
    "pytest.raises",
    "assertRaises",
    "with raises(",
    "expected failure",
    "should fail",
)

PACK_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "task_pack_v1": {
        "total": 300,
        "splits": {"train": 200, "dev": 50, "test": 50},
        "quick": 18,
        "difficulty": {"easy": 105, "medium": 135, "hard": 60},
        "strength_policy": {
            "min_strength_score": 18,
            "max_low_strength_fraction": 0.25,
            "max_mutation_skip_fraction": 0.05,
            "require_mutation_caught": True,
        },
    },
    "task_pack_v2": {
        "total": 500,
        "splits": {"train": 340, "dev": 80, "test": 80},
        "quick": 30,
        "difficulty": {"easy": 175, "medium": 225, "hard": 100},
        "strength_policy": {
            "min_strength_score": 22,
            "max_low_strength_fraction": 0.20,
            "max_mutation_skip_fraction": 0.05,
            "require_mutation_caught": True,
        },
    },
}


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


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _score_distribution(values: list[int]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0.0,
            "median": 0.0,
            "p10": 0.0,
            "p90": 0.0,
            "deciles": {},
        }

    ordered = sorted(values)

    def _percentile(pct: float) -> float:
        if len(ordered) == 1:
            return float(ordered[0])
        position = (len(ordered) - 1) * pct
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        if lower == upper:
            return float(ordered[lower])
        lower_value = ordered[lower]
        upper_value = ordered[upper]
        return float(lower_value + (upper_value - lower_value) * (position - lower))

    deciles: dict[str, int] = {}
    for value in ordered:
        bucket_start = min(90, (value // 10) * 10)
        label = f"{bucket_start:02d}-{bucket_start + 9:02d}"
        deciles[label] = deciles.get(label, 0) + 1

    return {
        "count": len(ordered),
        "min": int(ordered[0]),
        "max": int(ordered[-1]),
        "mean": round(mean(ordered), 2),
        "median": round(float(median(ordered)), 2),
        "p10": round(_percentile(0.10), 2),
        "p90": round(_percentile(0.90), 2),
        "deciles": dict(sorted(deciles.items())),
    }


def _task_test_files(task_dir: Path) -> list[Path]:
    tests_dir = task_dir / "tests"
    if not tests_dir.exists():
        return []
    return sorted(path for path in tests_dir.rglob("test_*.py") if path.is_file())


def _source_modules(task_dir: Path) -> dict[str, Path]:
    src_dir = task_dir / "src"
    if not src_dir.exists():
        return {}

    modules: dict[str, Path] = {}
    for path in sorted(src_dir.rglob("*.py")):
        if not path.is_file() or path.name == "__init__.py":
            continue
        rel = path.relative_to(src_dir).with_suffix("")
        module_name = ".".join(rel.parts)
        modules[module_name] = path
    return modules


def _source_cross_imports(src_modules: dict[str, Path]) -> bool:
    if len(src_modules) < 2:
        return False
    module_names = set(src_modules)

    for current_module, path in src_modules.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue

        for node in ast.walk(tree):
            target: str | None = None
            if isinstance(node, ast.ImportFrom):
                if isinstance(node.module, str) and node.module.startswith("src."):
                    target = node.module[4:]
                elif node.level > 0 and isinstance(node.module, str):
                    target = node.module
                elif isinstance(node.module, str) and node.module in module_names:
                    target = node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name.startswith("src."):
                        candidate = name[4:]
                    else:
                        candidate = name
                    if candidate in module_names:
                        target = candidate
                        break

            if target and target in module_names and target != current_module:
                return True
    return False


def _collect_test_hints(
    *,
    test_files: list[Path],
    available_modules: set[str],
) -> tuple[int, list[str], bool, dict[str, int], dict[str, set[str]]]:
    assertion_count = 0
    edge_keyword_hits: set[str] = set()
    negative_test_present = False
    module_votes: dict[str, int] = {}
    symbol_hints: dict[str, set[str]] = {}

    for test_file in test_files:
        try:
            text = test_file.read_text(encoding="utf-8")
        except OSError:
            continue

        lowered = text.lower()
        for keyword in EDGE_CASE_KEYWORDS:
            if keyword in lowered:
                edge_keyword_hits.add(keyword)
        if any(pattern in lowered for pattern in NEGATIVE_TEST_PATTERNS):
            negative_test_present = True

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                assertion_count += 1
                continue

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    attr_name = node.func.attr
                    if attr_name.startswith("assert"):
                        assertion_count += 1
                    if attr_name in {"raises", "assertRaises", "fail"}:
                        negative_test_present = True
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name.startswith("assert"):
                        assertion_count += 1
                    if func_name in {"raises", "fail"}:
                        negative_test_present = True

            if isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    context = item.context_expr
                    if isinstance(context, ast.Call):
                        if isinstance(context.func, ast.Attribute) and context.func.attr == "raises":
                            negative_test_present = True
                        elif isinstance(context.func, ast.Name) and context.func.id == "raises":
                            negative_test_present = True

            if isinstance(node, ast.ImportFrom):
                resolved_module: str | None = None
                if isinstance(node.module, str) and node.module.startswith("src."):
                    resolved_module = node.module[4:]
                elif isinstance(node.module, str) and node.module in available_modules:
                    resolved_module = node.module

                if resolved_module:
                    module_votes[resolved_module] = module_votes.get(resolved_module, 0) + 1
                    symbols = symbol_hints.setdefault(resolved_module, set())
                    for alias in node.names:
                        if alias.name != "*":
                            symbols.add(alias.name)
                elif node.module == "src":
                    for alias in node.names:
                        if alias.name in available_modules:
                            module_votes[alias.name] = module_votes.get(alias.name, 0) + 1

            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name[4:] if alias.name.startswith("src.") else alias.name
                    if module_name in available_modules:
                        module_votes[module_name] = module_votes.get(module_name, 0) + 1

    return (
        assertion_count,
        sorted(edge_keyword_hits),
        negative_test_present,
        module_votes,
        symbol_hints,
    )


def _strength_score(
    *,
    assertion_count: int,
    edge_keyword_count: int,
    multi_file_interaction: bool,
    negative_test_present: bool,
) -> int:
    assert_score = min(50, assertion_count * 5)
    edge_score = min(20, edge_keyword_count * 4)
    interaction_score = 15 if multi_file_interaction else 0
    negative_score = 15 if negative_test_present else 0
    return int(max(0, min(100, assert_score + edge_score + interaction_score + negative_score)))


def _function_is_generator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(isinstance(item, (ast.Yield, ast.YieldFrom)) for item in ast.walk(node))


def _strategy_for_mutation(task_id: str, module_name: str, symbol_name: str) -> str:
    digest = hashlib.sha256(f"{task_id}:{module_name}:{symbol_name}".encode("utf-8")).hexdigest()
    selector = int(digest[:4], 16) % 3
    if selector == 0:
        return "return_none"
    if selector == 1:
        return "return_zero"
    return "raise_runtime_error"


def mutate_source_with_wrong_patch(
    *,
    task_id: str,
    module_name: str,
    source_text: str,
    symbol_hints: set[str] | None = None,
) -> tuple[str | None, dict[str, str] | None, str | None]:
    """Return (mutated_source, mutation_target, skip_reason)."""
    hints = symbol_hints or set()
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return None, None, "module_parse_error"

    function_candidates: list[tuple[int, int, str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    class_method_candidates: list[
        tuple[int, int, str, ast.FunctionDef | ast.AsyncFunctionDef]
    ] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                priority = 3
            else:
                priority = 1
            if node.name in hints:
                priority = 0
            function_candidates.append((priority, node.lineno, node.name, node))
            continue

        if isinstance(node, ast.ClassDef):
            for member in node.body:
                if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                qual_name = f"{node.name}.{member.name}"
                if member.name.startswith("_"):
                    priority = 6
                else:
                    priority = 4
                if member.name in hints or node.name in hints or qual_name in hints:
                    priority = 2
                class_method_candidates.append((priority, member.lineno, qual_name, member))

    candidates = sorted(function_candidates + class_method_candidates)
    if not candidates:
        return None, None, "no_function_candidate"

    _, _, symbol_name, target = candidates[0]
    strategy = _strategy_for_mutation(task_id, module_name, symbol_name)
    if _function_is_generator(target):
        strategy = "raise_runtime_error"

    if strategy == "raise_runtime_error":
        new_stmt: ast.stmt = ast.Raise(
            exc=ast.Call(
                func=ast.Name(id="RuntimeError", ctx=ast.Load()),
                args=[ast.Constant(value="mwb_counterexample_mutation")],
                keywords=[],
            ),
            cause=None,
        )
    elif strategy == "return_zero":
        new_stmt = ast.Return(value=ast.Constant(value=0))
    else:
        new_stmt = ast.Return(value=ast.Constant(value=None))

    target.body = [new_stmt]
    ast.fix_missing_locations(tree)
    try:
        mutated_source = ast.unparse(tree).rstrip() + "\n"
    except Exception:
        return None, None, "module_unparse_error"

    mutation_target = {
        "module": module_name,
        "symbol": symbol_name,
        "strategy": strategy,
    }
    return mutated_source, mutation_target, None


def _select_mutation_module(
    *,
    src_modules: dict[str, Path],
    module_votes: dict[str, int],
) -> str | None:
    if not src_modules:
        return None
    if not module_votes:
        return sorted(src_modules)[0]

    ranked = sorted(
        module_votes.items(),
        key=lambda item: (-item[1], item[0]),
    )
    for module_name, _ in ranked:
        if module_name in src_modules:
            return module_name
    return sorted(src_modules)[0]


def _mutation_sample(task_ids: list[str], sample_size: int) -> set[str]:
    if sample_size >= len(task_ids):
        return set(task_ids)
    ranked = sorted(
        task_ids,
        key=lambda task_id: hashlib.sha256(task_id.encode("utf-8")).hexdigest(),
    )
    return set(ranked[:sample_size])


def _run_mutation_counterexample(
    *,
    task_id: str,
    task_dir: Path,
    source_module: str | None,
    symbol_hints: set[str],
    mutation_timeout_seconds: int,
) -> dict[str, Any]:
    mutation_report: dict[str, Any] = {
        "starter_test_passed": None,
        "starter_test_exit_code": None,
        "starter_test_timed_out": None,
        "mutation_status": "skipped",
        "mutation_skip_reason": None,
        "mutation_test_passed": None,
        "mutation_test_exit_code": None,
        "mutation_test_timed_out": None,
        "mutation_target": None,
    }

    with tempfile.TemporaryDirectory(prefix=f"mwb_strength_{task_id}_") as temp_name:
        workdir = Path(temp_name)
        shutil.copytree(task_dir, workdir, dirs_exist_ok=True)

        starter_run = run_pytest(workdir, timeout_seconds=mutation_timeout_seconds)
        mutation_report["starter_test_passed"] = bool(starter_run.passed)
        mutation_report["starter_test_exit_code"] = int(starter_run.exit_code)
        mutation_report["starter_test_timed_out"] = bool(starter_run.timed_out)

        src_modules = _source_modules(workdir)
        if not source_module:
            mutation_report["mutation_skip_reason"] = "no_source_module"
            return mutation_report
        target_path = src_modules.get(source_module)
        if target_path is None or not target_path.exists():
            mutation_report["mutation_skip_reason"] = "target_module_missing"
            return mutation_report

        source_text = target_path.read_text(encoding="utf-8")
        mutated_source, target_meta, skip_reason = mutate_source_with_wrong_patch(
            task_id=task_id,
            module_name=source_module,
            source_text=source_text,
            symbol_hints=symbol_hints,
        )
        if mutated_source is None or target_meta is None:
            mutation_report["mutation_skip_reason"] = skip_reason or "mutation_generation_failed"
            return mutation_report

        target_path.write_text(mutated_source, encoding="utf-8")
        mutated_run = run_pytest(workdir, timeout_seconds=mutation_timeout_seconds)
        mutation_report["mutation_target"] = target_meta
        mutation_report["mutation_test_passed"] = bool(mutated_run.passed)
        mutation_report["mutation_test_exit_code"] = int(mutated_run.exit_code)
        mutation_report["mutation_test_timed_out"] = bool(mutated_run.timed_out)
        mutation_report["mutation_status"] = "not_caught" if mutated_run.passed else "caught"
        return mutation_report


def _load_strength_allowlist(allowlist_path: Path | None) -> dict[str, Any]:
    defaults = {
        "allowed_low_strength": [],
        "allowed_mutation_skip": [],
        "allowed_mutation_not_caught": [],
    }
    if allowlist_path is None or not allowlist_path.exists():
        return defaults
    try:
        payload = json.loads(allowlist_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return defaults
    if not isinstance(payload, dict):
        return defaults

    resolved = dict(defaults)
    for key in defaults:
        value = payload.get(key)
        if isinstance(value, list):
            resolved[key] = [str(item) for item in value if isinstance(item, str)]

    for key in ("min_strength_score", "max_low_strength_fraction", "max_mutation_skip_fraction"):
        if isinstance(payload.get(key), (int, float)):
            resolved[key] = float(payload[key])
    if isinstance(payload.get("require_mutation_caught"), bool):
        resolved["require_mutation_caught"] = payload["require_mutation_caught"]
    return resolved


def build_task_strength_report(
    *,
    root: Path,
    payload: dict[str, Any],
    strict: bool,
    allowlist_path: Path | None = None,
    run_mutation: bool = True,
    mutation_timeout_seconds: int = DEFAULT_MUTATION_TIMEOUT_SECONDS,
    mutation_sample_limit: int = DEFAULT_MUTATION_SAMPLE_LIMIT,
) -> dict[str, Any]:
    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list):
        return {
            "enabled": False,
            "strict": strict,
            "reason": "metadata_tasks_not_a_list",
            "tasks": [],
        }

    pack_name = str(payload.get("pack_name", ""))
    policy_defaults = dict(PACK_EXPECTATIONS.get(pack_name, {}).get("strength_policy", {}))
    allowlist = _load_strength_allowlist(allowlist_path)
    policy = {
        "min_strength_score": int(allowlist.get("min_strength_score", policy_defaults.get("min_strength_score", 20))),
        "max_low_strength_fraction": float(
            allowlist.get("max_low_strength_fraction", policy_defaults.get("max_low_strength_fraction", 0.20))
        ),
        "max_mutation_skip_fraction": float(
            allowlist.get("max_mutation_skip_fraction", policy_defaults.get("max_mutation_skip_fraction", 0.05))
        ),
        "require_mutation_caught": bool(
            allowlist.get("require_mutation_caught", policy_defaults.get("require_mutation_caught", True))
        ),
    }

    task_ids = [
        str(task["task_id"])
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    ]
    evaluate_all_mutations = bool(run_mutation and strict)
    if not run_mutation:
        evaluated_mutation_tasks: set[str] = set()
        mutation_mode = "disabled"
    elif evaluate_all_mutations:
        evaluated_mutation_tasks = set(task_ids)
        mutation_mode = "full"
    else:
        evaluated_mutation_tasks = _mutation_sample(task_ids, min(len(task_ids), max(1, mutation_sample_limit)))
        mutation_mode = "sample"

    task_reports: list[dict[str, Any]] = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id", ""))
        rel_path = str(task.get("path", ""))
        task_dir = (root / rel_path).resolve()
        test_files = _task_test_files(task_dir)
        src_modules = _source_modules(task_dir)
        available_modules = set(src_modules)
        (
            assertion_count,
            edge_keyword_hits,
            negative_test_present,
            module_votes,
            symbol_hints_by_module,
        ) = _collect_test_hints(
            test_files=test_files,
            available_modules=available_modules,
        )
        multi_file_interaction = len([name for name, score in module_votes.items() if score > 0]) >= 2
        multi_file_interaction = multi_file_interaction or _source_cross_imports(src_modules)
        strength_score = _strength_score(
            assertion_count=assertion_count,
            edge_keyword_count=len(edge_keyword_hits),
            multi_file_interaction=multi_file_interaction,
            negative_test_present=negative_test_present,
        )

        selected_module = _select_mutation_module(src_modules=src_modules, module_votes=module_votes)
        task_report: dict[str, Any] = {
            "task_id": task_id,
            "assertion_count": int(assertion_count),
            "edge_keyword_hits": edge_keyword_hits,
            "edge_keyword_count": len(edge_keyword_hits),
            "multi_file_interaction": bool(multi_file_interaction),
            "negative_test_present": bool(negative_test_present),
            "strength_score": int(strength_score),
            "mutation_status": "not_run",
            "mutation_skip_reason": "non_strict_sampling",
            "mutation_target": None,
            "starter_test_passed": None,
            "starter_test_exit_code": None,
            "starter_test_timed_out": None,
            "mutation_test_passed": None,
            "mutation_test_exit_code": None,
            "mutation_test_timed_out": None,
        }

        if task_id in evaluated_mutation_tasks and task_dir.exists():
            symbol_hints = symbol_hints_by_module.get(selected_module or "", set())
            mutation_report = _run_mutation_counterexample(
                task_id=task_id,
                task_dir=task_dir,
                source_module=selected_module,
                symbol_hints=symbol_hints,
                mutation_timeout_seconds=mutation_timeout_seconds,
            )
            task_report.update(mutation_report)
        elif task_id in evaluated_mutation_tasks and not task_dir.exists():
            task_report["mutation_status"] = "skipped"
            task_report["mutation_skip_reason"] = "task_path_missing"

        task_reports.append(task_report)

    task_reports.sort(key=lambda row: row["task_id"])
    scores = [int(row["strength_score"]) for row in task_reports]
    mutation_status_counts = Counter(str(row.get("mutation_status")) for row in task_reports)
    evaluated_mutations = mutation_status_counts.get("caught", 0) + mutation_status_counts.get("not_caught", 0)
    skipped_mutations = mutation_status_counts.get("skipped", 0)
    mutation_coverage_base = evaluated_mutations + skipped_mutations
    non_skipped_ratio = (
        (evaluated_mutations / mutation_coverage_base) if mutation_coverage_base else 1.0
    )

    low_strength_ids = [
        row["task_id"]
        for row in task_reports
        if int(row["strength_score"]) < int(policy["min_strength_score"])
    ]
    not_caught_ids = [row["task_id"] for row in task_reports if row.get("mutation_status") == "not_caught"]
    skipped_ids = [row["task_id"] for row in task_reports if row.get("mutation_status") == "skipped"]

    allowed_low_strength = set(allowlist.get("allowed_low_strength", []))
    allowed_mutation_skip = set(allowlist.get("allowed_mutation_skip", []))
    allowed_mutation_not_caught = set(allowlist.get("allowed_mutation_not_caught", []))

    low_strength_non_allowlisted = sorted(task_id for task_id in low_strength_ids if task_id not in allowed_low_strength)
    skipped_non_allowlisted = sorted(task_id for task_id in skipped_ids if task_id not in allowed_mutation_skip)
    not_caught_non_allowlisted = sorted(
        task_id for task_id in not_caught_ids if task_id not in allowed_mutation_not_caught
    )

    strict_errors: list[str] = []
    low_fraction = (len(low_strength_non_allowlisted) / len(task_reports)) if task_reports else 0.0
    if low_fraction > float(policy["max_low_strength_fraction"]):
        strict_errors.append(
            "Low-strength tasks exceed threshold: "
            f"{len(low_strength_non_allowlisted)}/{len(task_reports)} "
            f"({low_fraction:.2%}) > allowed {float(policy['max_low_strength_fraction']):.2%}"
        )
    skip_fraction = (len(skipped_non_allowlisted) / mutation_coverage_base) if mutation_coverage_base else 0.0
    if mutation_coverage_base and skip_fraction > float(policy["max_mutation_skip_fraction"]):
        strict_errors.append(
            "Mutation skips exceed threshold: "
            f"{len(skipped_non_allowlisted)}/{mutation_coverage_base} "
            f"({skip_fraction:.2%}) > allowed {float(policy['max_mutation_skip_fraction']):.2%}"
        )
    if bool(policy["require_mutation_caught"]) and not_caught_non_allowlisted:
        strict_errors.append(
            f"{len(not_caught_non_allowlisted)} task(s) did not fail on deterministic wrong patch."
        )
    if run_mutation and evaluate_all_mutations and non_skipped_ratio < 0.95:
        strict_errors.append(
            "Non-skipped mutation ratio is below 95%: "
            f"{non_skipped_ratio:.2%} (expected >= 95.00%)"
        )

    return {
        "enabled": True,
        "strict": strict,
        "allowlist_path": str(allowlist_path) if allowlist_path else None,
        "allowlist": {
            "allowed_low_strength_count": len(allowed_low_strength),
            "allowed_mutation_skip_count": len(allowed_mutation_skip),
            "allowed_mutation_not_caught_count": len(allowed_mutation_not_caught),
        },
        "policy": policy,
        "mutation_sampling": {
            "mode": mutation_mode,
            "sample_limit": int(mutation_sample_limit),
            "evaluated_task_count": int(len(evaluated_mutation_tasks)),
            "total_task_count": int(len(task_reports)),
        },
        "distribution": _score_distribution(scores),
        "mutation_stats": {
            "status_counts": dict(sorted(mutation_status_counts.items())),
            "evaluated_count": int(evaluated_mutations),
            "skip_count": int(skipped_mutations),
            "non_skipped_ratio": round(non_skipped_ratio, 4),
            "not_caught_count": len(not_caught_ids),
            "not_caught_non_allowlisted_count": len(not_caught_non_allowlisted),
            "skipped_non_allowlisted_count": len(skipped_non_allowlisted),
        },
        "strict_evaluation": {
            "would_fail": bool(strict_errors),
            "errors": strict_errors,
            "low_strength_non_allowlisted_count": len(low_strength_non_allowlisted),
            "low_strength_non_allowlisted_ids": low_strength_non_allowlisted,
            "mutation_not_caught_non_allowlisted_ids": not_caught_non_allowlisted,
            "mutation_skipped_non_allowlisted_ids": skipped_non_allowlisted,
        },
        "tasks": task_reports,
    }


def validate_task_pack_payload(
    *,
    root: Path,
    payload: dict[str, Any],
    schema: dict[str, Any],
    required_task_files: list[str] | None = None,
    strict: bool = False,
    return_report: bool = False,
    allowlist_path: Path | None = None,
    mutation_timeout_seconds: int = DEFAULT_MUTATION_TIMEOUT_SECONDS,
    mutation_sample_limit: int = DEFAULT_MUTATION_SAMPLE_LIMIT,
    expected_pack: dict[str, Any] | None = None,
    allow_unknown_pack: bool = False,
) -> tuple[bool, list[str]] | tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    report: dict[str, Any] = {
        "pack_name": str(payload.get("pack_name", "")),
        "strict": bool(strict),
        "schema_errors": [],
        "strength_gates": {"enabled": False, "reason": "not_computed"},
    }

    if not isinstance(schema, dict):
        base_errors = ["metadata schema must be a JSON object"]
        if return_report:
            report["schema_errors"] = base_errors
            return False, base_errors, report
        return False, base_errors

    _validate_schema_node(value=payload, schema=schema, path="metadata", errors=errors)
    report["schema_errors"] = list(errors)

    missing_top = sorted(REQUIRED_TOP_LEVEL_KEYS - set(payload))
    if missing_top:
        errors.append(f"metadata.json missing top-level key(s): {', '.join(missing_top)}")
        if return_report:
            report["schema_errors"] = list(errors)
            return False, errors, report
        return False, errors

    pack_name = str(payload.get("pack_name", ""))
    if expected_pack is not None:
        expected = expected_pack
    elif pack_name in PACK_EXPECTATIONS:
        expected = PACK_EXPECTATIONS[pack_name]
    elif allow_unknown_pack:
        expected = {}
    else:
        known = ", ".join(sorted(PACK_EXPECTATIONS))
        errors.append(f"Unsupported pack_name `{pack_name}`. Known: {known}")
        if return_report:
            report["schema_errors"] = list(errors)
            return False, errors, report
        return False, errors

    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("metadata.json: `tasks` must be a list")
        if return_report:
            report["schema_errors"] = list(errors)
            return False, errors, report
        return False, errors

    files_required = required_task_files or DEFAULT_REQUIRED_TASK_FILES
    seen_ids: set[str] = set()
    split_counts = {"train": 0, "dev": 0, "test": 0}
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0}

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

        difficulty = str(task["difficulty"])
        if difficulty not in difficulty_counts:
            errors.append(f"Invalid difficulty for {task_id}: {difficulty}")
        else:
            difficulty_counts[difficulty] += 1

        rel_path = str(task["path"])
        task_dir = (root / rel_path).resolve()
        if not task_dir.exists():
            errors.append(f"Task path missing for {task_id}: {task_dir}")
            continue

        for rel in files_required:
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

    expected_total = expected.get("total")
    if isinstance(expected_total, (int, float)) and not isinstance(expected_total, bool):
        expected_total_int = int(expected_total)
        if len(tasks) != expected_total_int:
            errors.append(f"Expected {expected_total_int} tasks, found {len(tasks)}")

    expected_splits = expected.get("splits")
    if isinstance(expected_splits, dict):
        normalized_splits = {
            "train": int(expected_splits.get("train", 0)),
            "dev": int(expected_splits.get("dev", 0)),
            "test": int(expected_splits.get("test", 0)),
        }
        if split_counts != normalized_splits:
            errors.append(f"Unexpected split counts: {split_counts}")

    quick_count = sum(1 for task in tasks if isinstance(task, dict) and bool(task.get("quick")))
    expected_quick = expected.get("quick")
    if isinstance(expected_quick, (int, float)) and not isinstance(expected_quick, bool):
        expected_quick_int = int(expected_quick)
        if quick_count != expected_quick_int:
            errors.append(f"Expected quick count {expected_quick_int}, found {quick_count}")

    expected_difficulty = expected.get("difficulty") if isinstance(expected, dict) else None
    if isinstance(expected_difficulty, dict) and difficulty_counts != expected_difficulty:
        errors.append(f"Unexpected difficulty counts: {difficulty_counts}")

    allowlist = allowlist_path or (root / "strength_allowlist.json")
    strength_report = build_task_strength_report(
        root=root,
        payload=payload,
        strict=strict,
        allowlist_path=allowlist,
        mutation_timeout_seconds=mutation_timeout_seconds,
        mutation_sample_limit=mutation_sample_limit,
    )
    report["strength_gates"] = strength_report
    if strict:
        strict_errors = strength_report.get("strict_evaluation", {}).get("errors", [])
        for issue in strict_errors:
            errors.append(f"Strength gate failure: {issue}")

    ok = not errors
    if return_report:
        report["schema_errors"] = [item for item in errors if not item.startswith("Strength gate failure:")]
        return ok, errors, report
    return ok, errors
