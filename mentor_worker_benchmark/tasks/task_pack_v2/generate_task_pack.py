from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

PACK_NAME = "task_pack_v2"
PACK_VERSION = "2.0.0"
DEFAULT_SEED = 1337
MINI_TASKS_PER_CATEGORY = 50

V1_CATEGORIES = [
    "string_regex_parsing",
    "ds_algo",
    "file_io_serialization",
    "concurrency_basics",
    "numerical_edge_cases",
    "multi_file_mini_module",
]

MINI_CATEGORIES = [
    "mini_repo_bugfix",
    "mini_repo_feature",
    "mini_repo_cli",
    "mini_repo_tool_sim",
]

CATEGORY_ORDER = V1_CATEGORIES + MINI_CATEGORIES

WORD_BANK = [
    "atlas",
    "beacon",
    "cinder",
    "delta",
    "ember",
    "fable",
    "grove",
    "harbor",
    "ion",
    "jade",
    "kepler",
    "lumen",
    "mosaic",
    "nova",
    "onyx",
    "pioneer",
    "quartz",
    "ripple",
    "signal",
    "timber",
    "umbra",
    "vector",
    "willow",
    "xylem",
    "yonder",
    "zenith",
]


@dataclass(slots=True)
class GeneratedTask:
    task_id: str
    title: str
    category: str
    difficulty: str
    files: dict[str, str]


def _task_seed(seed: int, category_index: int, task_index: int) -> int:
    global_index = category_index * 1000 + task_index
    return seed * 1009 + global_index * 9173 + 17


def _pick_words(rng: random.Random, count: int) -> list[str]:
    return rng.sample(WORD_BANK, k=count)


def _read_task_dir_files(task_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(task_dir).as_posix()
        files[rel] = path.read_text(encoding="utf-8")
    return files


def _load_v1_tasks() -> list[GeneratedTask]:
    v1_root = Path(__file__).resolve().parent.parent / "task_pack_v1"
    metadata = json.loads((v1_root / "metadata.json").read_text(encoding="utf-8"))

    loaded: list[GeneratedTask] = []
    for row in sorted(metadata["tasks"], key=lambda item: str(item["task_id"])):
        task_id = str(row["task_id"])
        task_dir = v1_root / str(row["path"])
        files = _read_task_dir_files(task_dir)
        loaded.append(
            GeneratedTask(
                task_id=task_id,
                title=str(row["title"]),
                category=str(row["category"]),
                difficulty=str(row["difficulty"]),
                files=files,
            )
        )
    return loaded


def _mini_bugfix_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    tag_a, tag_b, tag_c = [word.lower() for word in _pick_words(rng, 3)]
    delimiter = ["|", ";", ","][idx % 3]
    threshold = 5 + (idx % 4)
    rows = [
        f"{tag_a}{delimiter}{threshold}{delimiter}core",
        f"{tag_b}{delimiter}{threshold + 2}{delimiter}edge",
        f"{tag_c}{delimiter}{threshold - 1}{delimiter}core",
        f"invalid line",
        f"{tag_a}{delimiter}{threshold + 7}{delimiter}core",
    ]
    raw_blob = "\\n".join(rows)

    expected_total = (threshold) + (threshold + 2) + (threshold - 1) + (threshold + 7)
    expected_above = 2  # strictly greater than threshold.
    expected_top = f"{tag_a}"

    files = {
        "prompt.md": dedent(
            f"""
            # Mini-Repo Bugfix ({difficulty})

            Fix the integration behavior across modules for `build_report` in `src/pipeline.py`.

            Input rows are delimited by `{delimiter}` and should flow through:
            - `src/loader.py` -> parse valid rows
            - `src/metrics.py` -> aggregate summary metrics
            - `src/pipeline.py` -> orchestrate end-to-end report

            Requirements:
            - Ignore malformed rows.
            - Count `above_threshold` with strict `>` comparison.
            - `top_label` should be the label with highest score (tie -> lexical).
            - Keep signatures unchanged.

            Example input:
            - `{tag_a}{delimiter}{threshold}{delimiter}core`
            - `{tag_b}{delimiter}{threshold + 2}{delimiter}edge`
            """
        ).strip()
        + "\n",
        "README.md": "Mini repo bugfix task.\n",
        "src/__init__.py": "from .pipeline import build_report\n\n__all__ = ['build_report']\n",
        "src/constants.py": f"DELIMITER = {delimiter!r}\nDEFAULT_THRESHOLD = {threshold}\n",
        "src/loader.py": dedent(
            """
            from .constants import DELIMITER


            def parse_rows(raw: str) -> list[dict[str, object]]:
                entries: list[dict[str, object]] = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = [part.strip() for part in line.split(DELIMITER)]
                    if len(parts) != 3:
                        continue
                    label, score_raw, bucket = parts
                    try:
                        score = int(score_raw)
                    except ValueError:
                        continue
                    entries.append({"label": label.lower(), "score": score, "bucket": bucket.lower()})
                return entries
            """
        ).strip()
        + "\n",
        "src/metrics.py": dedent(
            """
            def summarize(entries: list[dict[str, object]], threshold: int) -> dict[str, object]:
                if threshold < 0:
                    raise ValueError("threshold must be non-negative")
                total = sum(int(item["score"]) for item in entries)
                # Buggy: threshold comparison should be strict '>'.
                above_threshold = sum(1 for item in entries if int(item["score"]) >= threshold)
                # Buggy: chooses last label, not highest-scoring label.
                top_label = str(entries[-1]["label"]) if entries else None
                return {
                    "total": total,
                    "count": len(entries),
                    "above_threshold": above_threshold,
                    "top_label": top_label,
                }
            """
        ).strip()
        + "\n",
        "src/pipeline.py": dedent(
            """
            from .constants import DEFAULT_THRESHOLD
            from .loader import parse_rows
            from .metrics import summarize


            def build_report(raw: str, threshold: int = DEFAULT_THRESHOLD) -> dict[str, object]:
                entries = parse_rows(raw)
                return summarize(entries, threshold)
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            from src.pipeline import build_report


            def test_integration_report() -> None:
                report = build_report({raw_blob!r}, threshold={threshold})
                assert report["total"] == {expected_total}
                assert report["count"] == 4
                assert report["above_threshold"] == {expected_above}
                assert report["top_label"] == {expected_top!r}


            def test_empty_input() -> None:
                report = build_report("", threshold={threshold})
                assert report == {{
                    "total": 0,
                    "count": 0,
                    "above_threshold": 0,
                    "top_label": None,
                }}
            """
        ).strip()
        + "\n",
    }
    return GeneratedTask(task_id, f"Mini bugfix {idx:03d}", "mini_repo_bugfix", difficulty, files)


def _mini_feature_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    team_a, team_b = [word.lower() for word in _pick_words(rng, 2)]
    delimiter = ["|", ":", "="][idx % 3]
    rows = [
        f"task-{idx}-a{delimiter}{team_a}{delimiter}active{delimiter}{3 + idx % 2}",
        f"task-{idx}-b{delimiter}{team_b}{delimiter}deferred{delimiter}{4 + idx % 2}",
        f"task-{idx}-c{delimiter}{team_a}{delimiter}active{delimiter}6",
        f"bad row",
    ]
    raw_blob = "\\n".join(rows)
    expected_without_deferred = [f"task-{idx}-c", f"task-{idx}-a"]
    expected_with_deferred = [f"task-{idx}-c", f"task-{idx}-b", f"task-{idx}-a"]

    files = {
        "prompt.md": dedent(
            f"""
            # Mini-Repo Feature ({difficulty})

            Add feature support to `generate_plan` in `src/service.py`.

            Input format: `name{delimiter}owner{delimiter}status{delimiter}points`

            New requirements:
            - Respect `include_deferred` end-to-end.
            - Support optional `include_status_breakdown=True` and include a `status_breakdown` map.
            - Keep deterministic ordering by points desc then name asc.
            - Keep existing behavior for callers that do not use new feature flags.
            """
        ).strip()
        + "\n",
        "src/__init__.py": "from .service import generate_plan\n\n__all__ = ['generate_plan']\n",
        "src/parser.py": dedent(
            f"""
            DELIMITER = {delimiter!r}


            def parse_tasks(raw: str) -> list[dict[str, object]]:
                items: list[dict[str, object]] = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = [part.strip() for part in line.split(DELIMITER)]
                    if len(parts) != 4:
                        continue
                    name, owner, status, points_raw = parts
                    try:
                        points = int(points_raw)
                    except ValueError:
                        continue
                    items.append(
                        {{
                            "name": name.lower(),
                            "owner": owner.lower(),
                            "status": status.lower(),
                            "points": points,
                        }}
                    )
                return items
            """
        ).strip()
        + "\n",
        "src/planner.py": dedent(
            """
            def build_plan(
                items: list[dict[str, object]],
                *,
                min_points: int,
                include_deferred: bool = False,
            ) -> list[dict[str, object]]:
                filtered = []
                for item in items:
                    points = int(item["points"])
                    status = str(item["status"])
                    if points < min_points:
                        continue
                    # Buggy: this still excludes deferred items even when include_deferred=True.
                    if status == "deferred":
                        continue
                    filtered.append(item)
                return sorted(filtered, key=lambda item: (-int(item["points"]), str(item["name"])))
            """
        ).strip()
        + "\n",
        "src/formatter.py": dedent(
            """
            def render(plan: list[dict[str, object]], *, status_breakdown: dict[str, int] | None = None) -> dict[str, object]:
                payload = {
                    "count": len(plan),
                    "tasks": [str(item["name"]) for item in plan],
                }
                if status_breakdown is not None:
                    payload["status_breakdown"] = dict(status_breakdown)
                return payload
            """
        ).strip()
        + "\n",
        "src/service.py": dedent(
            """
            from .formatter import render
            from .parser import parse_tasks
            from .planner import build_plan


            def generate_plan(
                raw: str,
                *,
                min_points: int = 0,
                include_deferred: bool = False,
                include_status_breakdown: bool = False,
            ) -> dict[str, object]:
                items = parse_tasks(raw)
                # Buggy: include_deferred not threaded through.
                plan = build_plan(items, min_points=min_points, include_deferred=False)
                if include_status_breakdown:
                    # Buggy: missing real breakdown map.
                    return render(plan, status_breakdown={})
                return render(plan)
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            from src.service import generate_plan


            def test_existing_behavior_without_feature_flags() -> None:
                payload = generate_plan({raw_blob!r}, min_points=0)
                assert payload["tasks"] == {expected_without_deferred!r}


            def test_include_deferred_feature() -> None:
                payload = generate_plan({raw_blob!r}, min_points=0, include_deferred=True)
                assert payload["tasks"] == {expected_with_deferred!r}


            def test_status_breakdown_feature() -> None:
                payload = generate_plan(
                    {raw_blob!r},
                    min_points=0,
                    include_deferred=True,
                    include_status_breakdown=True,
                )
                assert payload["status_breakdown"] == {{"active": 2, "deferred": 1}}
            """
        ).strip()
        + "\n",
    }
    return GeneratedTask(task_id, f"Mini feature {idx:03d}", "mini_repo_feature", difficulty, files)


def _mini_cli_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    _ = rng
    bias = (idx % 4) - 1
    values_text = f"{3 + idx % 4},{1 + idx % 2},{7 + idx % 3}"
    values = [int(part) for part in values_text.split(",")]
    expected_sum = sum(values) + bias
    expected_max = max(values) + bias
    expected_median = sorted(values)[len(values) // 2] + bias

    files = {
        "prompt.md": dedent(
            f"""
            # Mini-Repo CLI Task ({difficulty})

            Implement CLI behavior in `src/cli.py` for a local utility.

            Requirements:
            - Parse `--values` as comma-separated integers.
            - Support modes: `sum`, `max`, `median`.
            - Apply `--bias` to final numeric output.
            - `--as-json` prints a JSON object with `mode` and `value`.
            - Keep CLI entrypoint `main(argv: list[str] | None = None) -> int`.
            """
        ).strip()
        + "\n",
        "README.md": "CLI task with argparse behavior.\n",
        "src/__init__.py": "from .cli import main\n\n__all__ = ['main']\n",
        "src/parsing.py": dedent(
            """
            def parse_values(raw: str) -> list[int]:
                values: list[int] = []
                for part in raw.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    values.append(int(part))
                return values
            """
        ).strip()
        + "\n",
        "src/core.py": dedent(
            """
            def evaluate(values: list[int], *, mode: str, bias: int) -> int:
                if not values:
                    raise ValueError("values cannot be empty")
                if mode == "sum":
                    return sum(values) + bias
                if mode == "max":
                    return max(values) + bias
                # Buggy: missing median support.
                raise ValueError(f"unsupported mode: {mode}")
            """
        ).strip()
        + "\n",
        "src/cli.py": dedent(
            """
            import argparse
            import json

            from .core import evaluate
            from .parsing import parse_values


            def main(argv: list[str] | None = None) -> int:
                parser = argparse.ArgumentParser()
                parser.add_argument("--values", required=True)
                parser.add_argument("--mode", default="sum")
                parser.add_argument("--bias", type=int, default=0)
                parser.add_argument("--as-json", action="store_true")
                args = parser.parse_args(argv)

                values = parse_values(args.values)
                value = evaluate(values, mode=args.mode, bias=args.bias)
                # Buggy: ignores --as-json.
                print(value)
                return 0
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            import json

            from src.cli import main


            def test_cli_sum_mode(capsys) -> None:
                code = main(["--values", {values_text!r}, "--mode", "sum", "--bias", {bias!r}])
                assert code == 0
                output = capsys.readouterr().out.strip()
                assert output == str({expected_sum})


            def test_cli_median_mode(capsys) -> None:
                code = main(["--values", {values_text!r}, "--mode", "median", "--bias", {bias!r}])
                assert code == 0
                output = capsys.readouterr().out.strip()
                assert output == str({expected_median})


            def test_cli_json_output(capsys) -> None:
                code = main(
                    ["--values", {values_text!r}, "--mode", "max", "--bias", {bias!r}, "--as-json"]
                )
                assert code == 0
                payload = json.loads(capsys.readouterr().out.strip())
                assert payload == {{"mode": "max", "value": {expected_max}}}
            """
        ).strip()
        + "\n",
    }
    return GeneratedTask(task_id, f"Mini cli {idx:03d}", "mini_repo_cli", difficulty, files)


def _mini_tool_sim_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    file_a, file_b = [word.lower() for word in _pick_words(rng, 2)]
    report_lines = [
        f"RULE:unused_import|SEVERITY:warn|FILE:{file_a}.py|LINE:{10 + idx}",
        f"RULE:unsafe_eval|SEVERITY:error|FILE:{file_b}.py|LINE:{20 + idx}",
        f"RULE:line_too_long|SEVERITY:info|FILE:{file_a}.py|LINE:{30 + idx}",
        f"RULE:unused_import|SEVERITY:warn|FILE:{file_b}.py|LINE:{40 + idx}",
    ]
    report_blob = "\\n".join(report_lines) + "\\n"

    files = {
        "prompt.md": dedent(
            f"""
            # Mini-Repo Tool-Use Simulation ({difficulty})

            This task simulates a local analyzer workflow completely offline.

            A tool output file is provided in `data/analyzer_output.txt`.
            Update parsing and aggregation in:
            - `src/parser.py`
            - `src/pipeline.py`

            Requirements:
            - Parse tool lines formatted as `RULE:<rule>|SEVERITY:<level>|FILE:<path>|LINE:<n>`.
            - Severity ordering: `info < warn < error`.
            - `summarize_from_report(path, min_severity)` should filter by min severity and return:
              - `count`
              - `by_severity`
              - `top_rule` (highest frequency, tie -> lexical)

            You do not need to execute any tool; use the provided file contents.
            """
        ).strip()
        + "\n",
        "README.md": "Offline tool-use simulation task.\n",
        "tools/local_analyzer.py": dedent(
            """
            #!/usr/bin/env python3
            \"\"\"Example local analyzer script.

            This script is intentionally not executed by tests.
            It documents the expected output format consumed by src/parser.py.
            \"\"\"

            if __name__ == "__main__":
                print("RULE:example|SEVERITY:warn|FILE:sample.py|LINE:1")
            """
        ).strip()
        + "\n",
        "data/analyzer_output.txt": report_blob,
        "src/__init__.py": "from .pipeline import summarize_from_report\n\n__all__ = ['summarize_from_report']\n",
        "src/parser.py": dedent(
            """
            def parse_findings(raw: str) -> list[dict[str, object]]:
                findings: list[dict[str, object]] = []
                for line in raw.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    # Buggy: tool format uses '|', but this parser uses ';'.
                    parts = [part.strip() for part in line.split(";")]
                    if len(parts) != 4:
                        continue
                    payload: dict[str, object] = {}
                    for part in parts:
                        key, value = part.split(":", 1)
                        payload[key.lower()] = value.strip().lower()
                    findings.append(payload)
                return findings
            """
        ).strip()
        + "\n",
        "src/pipeline.py": dedent(
            """
            from collections import Counter
            from pathlib import Path

            from .parser import parse_findings

            SEVERITY_RANK = {"info": 1, "warn": 2, "error": 3}


            def summarize_from_report(path: str, min_severity: str = "info") -> dict[str, object]:
                raw = Path(path).read_text(encoding="utf-8")
                findings = parse_findings(raw)
                min_rank = SEVERITY_RANK[min_severity]
                filtered = [
                    finding
                    for finding in findings
                    if SEVERITY_RANK.get(str(finding.get("severity", "info")), 0) >= min_rank
                ]
                rule_counts = Counter(str(finding.get("rule", "")) for finding in filtered)
                severity_counts = Counter(str(finding.get("severity", "")) for finding in filtered)
                top_rule = None
                if rule_counts:
                    top_rule = sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
                return {
                    "count": len(filtered),
                    "by_severity": dict(sorted(severity_counts.items())),
                    "top_rule": top_rule,
                }
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            """
            from pathlib import Path

            from src.pipeline import summarize_from_report


            def test_warn_threshold() -> None:
                report_path = Path("data/analyzer_output.txt")
                summary = summarize_from_report(str(report_path), min_severity="warn")
                assert summary["count"] == 3
                assert summary["by_severity"] == {"error": 1, "warn": 2}
                assert summary["top_rule"] == "unused_import"


            def test_error_threshold() -> None:
                report_path = Path("data/analyzer_output.txt")
                summary = summarize_from_report(str(report_path), min_severity="error")
                assert summary["count"] == 1
                assert summary["by_severity"] == {"error": 1}
                assert summary["top_rule"] == "unsafe_eval"
            """
        ).strip()
        + "\n",
    }
    return GeneratedTask(task_id, f"Mini tool sim {idx:03d}", "mini_repo_tool_sim", difficulty, files)


def _difficulty_sequence(easy: int, medium: int, hard: int, seed: int) -> list[str]:
    values = ["easy"] * easy + ["medium"] * medium + ["hard"] * hard
    rng = random.Random(seed)
    rng.shuffle(values)
    return values


def _mini_task_specs(seed: int) -> dict[str, list[str]]:
    # Added difficulties so combined corpus hits 35/45/20 exactly (175/225/100 over 500 tasks).
    plans = {
        "mini_repo_bugfix": (18, 22, 10),
        "mini_repo_feature": (18, 22, 10),
        "mini_repo_cli": (17, 23, 10),
        "mini_repo_tool_sim": (17, 23, 10),
    }
    return {
        category: _difficulty_sequence(easy, medium, hard, seed + idx * 211)
        for idx, (category, (easy, medium, hard)) in enumerate(plans.items())
    }


def _build_mini_tasks(seed: int) -> list[GeneratedTask]:
    difficulty_by_category = _mini_task_specs(seed)
    generated: list[GeneratedTask] = []

    generators = {
        "mini_repo_bugfix": _mini_bugfix_task,
        "mini_repo_feature": _mini_feature_task,
        "mini_repo_cli": _mini_cli_task,
        "mini_repo_tool_sim": _mini_tool_sim_task,
    }

    for category_index, category in enumerate(MINI_CATEGORIES):
        difficulties = difficulty_by_category[category]
        generator = generators[category]
        for idx in range(MINI_TASKS_PER_CATEGORY):
            task_id = f"v2_mini_{category.replace('mini_repo_', '')}_{idx:03d}"
            rng = random.Random(_task_seed(seed, len(V1_CATEGORIES) + category_index, idx))
            generated.append(generator(task_id, idx, rng, difficulties[idx]))
    return generated


def _assign_splits(task_ids: list[str], seed: int) -> dict[str, str]:
    shuffled = list(task_ids)
    random.Random(seed).shuffle(shuffled)

    split_map: dict[str, str] = {}
    for idx, task_id in enumerate(shuffled):
        if idx < 340:
            split_map[task_id] = "train"
        elif idx < 420:
            split_map[task_id] = "dev"
        else:
            split_map[task_id] = "test"
    return split_map


def _assign_quick_ids(tasks: list[GeneratedTask], split_map: dict[str, str], seed: int) -> set[str]:
    quick_ids: set[str] = set()
    for category_index, category in enumerate(CATEGORY_ORDER):
        candidates = [
            task.task_id
            for task in tasks
            if task.category == category and split_map[task.task_id] in {"dev", "test"}
        ]
        candidates = sorted(candidates)
        if len(candidates) < 3:
            raise RuntimeError(f"Not enough dev/test candidates for quick suite in category `{category}`.")
        category_rng = random.Random(seed + 7000 + category_index * 41)
        category_rng.shuffle(candidates)
        quick_ids.update(candidates[:3])
    return quick_ids


def _write_task_files(base: Path, task: GeneratedTask) -> None:
    task_dir = base / "tasks" / task.task_id
    for rel_path, content in task.files.items():
        path = task_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _validate_task_shape(task: GeneratedTask) -> None:
    required = {"prompt.md", "src/__init__.py", "tests/test_solution.py"}
    present = set(task.files)
    missing = required - present
    if missing:
        missing_label = ", ".join(sorted(missing))
        raise ValueError(f"Task `{task.task_id}` missing required file(s): {missing_label}")


def generate_task_pack(seed: int = DEFAULT_SEED) -> dict[str, object]:
    root = Path(__file__).resolve().parent
    tasks_root = root / "tasks"
    if tasks_root.exists():
        shutil.rmtree(tasks_root)
    tasks_root.mkdir(parents=True, exist_ok=True)

    tasks = _load_v1_tasks() + _build_mini_tasks(seed=seed)
    if len(tasks) != 500:
        raise RuntimeError(f"Expected 500 total tasks, found {len(tasks)}.")

    split_map = _assign_splits([task.task_id for task in tasks], seed=seed)
    quick_ids = _assign_quick_ids(tasks, split_map=split_map, seed=seed)

    metadata_tasks: list[dict[str, object]] = []
    for task in tasks:
        _validate_task_shape(task)
        _write_task_files(root, task)
        metadata_tasks.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "category": task.category,
                "difficulty": task.difficulty,
                "split": split_map[task.task_id],
                "quick": task.task_id in quick_ids,
                "path": f"tasks/{task.task_id}",
            }
        )

    metadata_tasks.sort(key=lambda row: str(row["task_id"]))
    counts = {
        "total": len(metadata_tasks),
        "train": sum(1 for row in metadata_tasks if row["split"] == "train"),
        "dev": sum(1 for row in metadata_tasks if row["split"] == "dev"),
        "test": sum(1 for row in metadata_tasks if row["split"] == "test"),
        "quick": sum(1 for row in metadata_tasks if row["quick"]),
    }
    expected_counts = {"total": 500, "train": 340, "dev": 80, "test": 80, "quick": 30}
    if counts != expected_counts:
        raise RuntimeError(f"Unexpected split counts: {counts}")

    difficulty_counts = {
        "easy": sum(1 for row in metadata_tasks if row["difficulty"] == "easy"),
        "medium": sum(1 for row in metadata_tasks if row["difficulty"] == "medium"),
        "hard": sum(1 for row in metadata_tasks if row["difficulty"] == "hard"),
    }
    if difficulty_counts != {"easy": 175, "medium": 225, "hard": 100}:
        raise RuntimeError(f"Unexpected difficulty counts: {difficulty_counts}")

    category_counts: dict[str, int] = {}
    for row in metadata_tasks:
        category = str(row["category"])
        category_counts[category] = category_counts.get(category, 0) + 1

    metadata = {
        "pack_name": PACK_NAME,
        "pack_version": PACK_VERSION,
        "generator_seed": seed,
        "categories": CATEGORY_ORDER,
        "counts": counts,
        "category_counts": category_counts,
        "tasks": metadata_tasks,
    }
    (root / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate task_pack_v2 benchmark tasks.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    metadata = generate_task_pack(seed=args.seed)
    counts = metadata["counts"]
    print(
        f"Generated {counts['total']} tasks "
        f"(train={counts['train']}, dev={counts['dev']}, test={counts['test']}, quick={counts['quick']})"
    )


if __name__ == "__main__":
    main()
