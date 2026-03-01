from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Callable

PACK_NAME = "task_pack_v1"
PACK_VERSION = "1.0.0"
DEFAULT_SEED = 1337
TASKS_PER_CATEGORY = 50

CATEGORY_ORDER = [
    "string_regex_parsing",
    "ds_algo",
    "file_io_serialization",
    "concurrency_basics",
    "numerical_edge_cases",
    "multi_file_mini_module",
]

MARKERS = ["@", "#", "$", "%", "&"]
SEPARATORS = [":", "=", "|", "->"]
DIFFICULTIES = ["easy", "medium", "hard"]

WORD_BANK = [
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mango",
    "nectar",
    "orion",
    "piper",
    "quartz",
    "raven",
    "sierra",
    "tango",
    "ultra",
    "vivid",
    "whiskey",
    "xenon",
    "yankee",
    "zebra",
    "apricot",
    "beacon",
    "cobalt",
    "drift",
    "ember",
    "fable",
    "glider",
    "harbor",
    "island",
    "jungle",
    "kepler",
    "lantern",
    "mercury",
    "nebula",
    "opal",
    "prairie",
    "quiver",
    "rocket",
    "sunset",
    "thunder",
    "umber",
    "velvet",
    "willow",
    "zenith",
    "amber",
    "blossom",
    "canyon",
    "dynamo",
    "elm",
    "frost",
    "grove",
    "hazel",
    "iris",
    "jasper",
    "kernel",
    "lotus",
    "meadow",
    "nova",
    "onyx",
    "pearl",
    "quest",
    "river",
    "solace",
    "timber",
    "utopia",
    "voyage",
    "warden",
    "xylem",
    "yonder",
    "zephyr",
    "acorn",
    "breeze",
    "cinder",
    "dawn",
    "eagle",
    "feather",
    "galaxy",
    "horizon",
    "ivory",
    "jade",
    "knight",
    "legend",
    "maple",
    "nectarine",
    "oasis",
    "pioneer",
    "quill",
    "ripple",
    "saffron",
    "temple",
    "unity",
    "vertex",
    "wander",
    "xpress",
    "yearling",
    "zen",
]


@dataclass(slots=True)
class GeneratedTask:
    task_id: str
    title: str
    category: str
    difficulty: str
    files: dict[str, str]


def _task_seed(seed: int, category_index: int, task_index: int, variant: int = 0) -> int:
    # Deterministic variant-aware seed for reproducible regeneration.
    global_index = category_index * TASKS_PER_CATEGORY + task_index
    return seed * 1009 + global_index * 9173 + variant * 104729 + 17


def _extract_assert_examples(tests_text: str, *, limit: int = 2) -> list[str]:
    examples: list[str] = []
    for line in tests_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("assert "):
            examples.append(stripped)
        if len(examples) >= limit:
            break
    return examples


def _append_prompt_quality_section(
    *,
    prompt: str,
    category: str,
    strict_level: int,
    tests_text: str,
) -> str:
    if strict_level <= 0:
        return prompt

    category_edge_hints = {
        "string_regex_parsing": [
            "Handle empty input gracefully.",
            "Preserve deterministic ordering when deduplicating.",
        ],
        "ds_algo": [
            "Handle empty datasets and non-positive limits.",
            "Keep tie-breaking deterministic.",
        ],
        "file_io_serialization": [
            "Handle empty files and malformed rows safely.",
            "Keep output ordering deterministic.",
        ],
        "concurrency_basics": [
            "Handle empty job lists and invalid worker counts.",
            "Preserve deterministic output ordering despite concurrency.",
        ],
        "numerical_edge_cases": [
            "Handle NaN/invalid ratios explicitly.",
            "Protect boundary trimming behavior.",
        ],
        "multi_file_mini_module": [
            "Handle empty and malformed input rows.",
            "Keep aggregation semantics deterministic.",
        ],
    }

    examples = _extract_assert_examples(tests_text, limit=2)
    lines: list[str] = [
        "## Quality Gate Expectations",
        "Implement all behavior required by tests, including edge-case handling and deterministic output.",
        "",
        "## Input/Output Examples",
    ]
    if examples:
        for idx, entry in enumerate(examples, start=1):
            lines.append(f"- Example {idx} input/output contract: `{entry}`")
    else:
        lines.append("- Input: see test fixtures for canonical inputs.")
        lines.append("- Output: satisfy exact assertion values in tests.")

    edge_hints = category_edge_hints.get(category, [])
    if edge_hints:
        lines.append("")
        lines.append("## Required Edge Cases")
        for hint in edge_hints:
            lines.append(f"- {hint}")

    if strict_level >= 2:
        lines.append("- Reject invalid inputs where required by the tests.")
    if strict_level >= 3:
        lines.append("- Avoid brittle shortcuts that only satisfy one fixture.")

    return prompt.rstrip() + "\n\n" + "\n".join(lines).rstrip() + "\n"


def _strict_test_snippet(category: str, strict_level: int) -> str:
    if strict_level <= 0:
        return ""

    snippets: dict[str, list[str]] = {
        "string_regex_parsing": [
            dedent(
                """
                def test_empty_input_returns_empty_list() -> None:
                    assert extract_markers("") == []
                """
            ).strip(),
            dedent(
                """
                def test_no_marker_returns_empty_list() -> None:
                    assert extract_markers("plain text without marker") == []
                """
            ).strip(),
        ],
        "ds_algo": [
            dedent(
                """
                def test_empty_records_returns_empty() -> None:
                    assert rank_products([], 3) == []
                """
            ).strip(),
            dedent(
                """
                def test_k_larger_than_population_is_safe() -> None:
                    records = [("alpha", 2), ("beta", 1), ("alpha", 1)]
                    assert rank_products(records, 10) == ["alpha", "beta"]
                """
            ).strip(),
        ],
        "file_io_serialization": [
            dedent(
                """
                def test_only_invalid_rows_produces_empty_object(tmp_path) -> None:
                    input_path = tmp_path / "invalid.csv"
                    output_path = tmp_path / "invalid.json"
                    input_path.write_text("user,amount,category\\n name , bad , cat \\n", encoding="utf-8")
                    summarize_transactions(str(input_path), str(output_path))
                    assert json.loads(output_path.read_text(encoding="utf-8")) == {}
                """
            ).strip(),
            dedent(
                """
                def test_whitespace_only_user_rows_are_ignored(tmp_path) -> None:
                    input_path = tmp_path / "spaces.csv"
                    output_path = tmp_path / "spaces.json"
                    input_path.write_text("user,amount,category\\n   ,3,x\\n", encoding="utf-8")
                    summarize_transactions(str(input_path), str(output_path))
                    assert json.loads(output_path.read_text(encoding="utf-8")) == {}
                """
            ).strip(),
        ],
        "concurrency_basics": [
            dedent(
                """
                def test_empty_jobs_returns_empty_result() -> None:
                    assert run_jobs([], max_workers=2) == []
                """
            ).strip(),
            dedent(
                """
                def test_single_job() -> None:
                    assert run_jobs([lambda: 42], max_workers=1) == [42]
                """
            ).strip(),
        ],
        "numerical_edge_cases": [
            dedent(
                """
                def test_single_value_no_trim() -> None:
                    assert trimmed_mean([5.0], 0.0) == pytest.approx(5.0)
                """
            ).strip(),
            dedent(
                """
                def test_negative_trim_ratio_raises() -> None:
                    with pytest.raises(ValueError):
                        trimmed_mean([1.0, 2.0, 3.0], -0.1)
                """
            ).strip(),
        ],
        "multi_file_mini_module": [
            dedent(
                """
                def test_malformed_only_input_returns_empty_report() -> None:
                    assert summarize("invalid line only") == {
                        "total": 0,
                        "unique_keys": 0,
                        "top_key": None,
                        "top_value": None,
                    }
                """
            ).strip(),
            dedent(
                """
                def test_trailing_blank_lines_are_safe() -> None:
                    payload = summarize("\\n\\n")
                    assert payload["total"] == 0
                    assert payload["unique_keys"] == 0
                """
            ).strip(),
        ],
    }

    category_snippets = snippets.get(category, [])
    if not category_snippets:
        return ""

    picked = category_snippets[: min(strict_level, len(category_snippets))]
    return "\n\n" + "\n\n".join(picked).rstrip() + "\n"


def _apply_quality_profile(task: GeneratedTask, strict_level: int) -> GeneratedTask:
    if strict_level <= 0:
        return task

    files = dict(task.files)
    tests_path = "tests/test_solution.py"
    prompt_path = "prompt.md"

    tests_text = files.get(tests_path, "")
    prompt_text = files.get(prompt_path, "")

    files[prompt_path] = _append_prompt_quality_section(
        prompt=prompt_text,
        category=task.category,
        strict_level=strict_level,
        tests_text=tests_text,
    )
    files[tests_path] = tests_text.rstrip() + _strict_test_snippet(task.category, strict_level)

    return GeneratedTask(
        task_id=task.task_id,
        title=task.title,
        category=task.category,
        difficulty=task.difficulty,
        files=files,
    )


def _pick_words(rng: random.Random, count: int) -> list[str]:
    return rng.sample(WORD_BANK, k=count)


def _rank_expected(records: list[tuple[str, int]], k: int) -> list[str]:
    if k <= 0:
        return []
    totals: dict[str, int] = {}
    for name, score in records:
        totals[name] = totals.get(name, 0) + score
    filtered = [(name, total) for name, total in totals.items() if total > 0]
    ordered = sorted(filtered, key=lambda item: (-item[1], item[0]))
    return [name for name, _ in ordered[:k]]


def _summarize_rows(rows: list[tuple[str, str, str]]) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for user_raw, amount_raw, category_raw in rows:
        user = user_raw.strip().lower()
        category = category_raw.strip().lower()
        if not user:
            continue
        try:
            amount = int(amount_raw.strip())
        except ValueError:
            continue
        if user not in summary:
            summary[user] = {"total": 0, "count": 0, "categories": set()}
        summary[user]["total"] = int(summary[user]["total"]) + amount
        summary[user]["count"] = int(summary[user]["count"]) + 1
        categories = summary[user]["categories"]
        assert isinstance(categories, set)
        categories.add(category)

    rendered: dict[str, dict[str, object]] = {}
    for user in sorted(summary):
        payload = summary[user]
        categories = payload["categories"]
        assert isinstance(categories, set)
        rendered[user] = {
            "total": payload["total"],
            "count": payload["count"],
            "categories": sorted(categories),
        }
    return rendered


def _trimmed_mean_oracle(values: list[float], trim_ratio: float) -> float:
    if not 0 <= trim_ratio < 0.5:
        raise ValueError("trim_ratio must be in [0, 0.5)")

    filtered = [value for value in values if value == value]
    if not filtered:
        raise ValueError("no finite values")

    ordered = sorted(filtered)
    trim_count = int(len(ordered) * trim_ratio)
    kept = ordered[trim_count : len(ordered) - trim_count]
    if not kept:
        raise ValueError("all values were trimmed")
    return sum(kept) / len(kept)


def _mini_module_expected(entries: list[tuple[str, int]]) -> dict[str, object]:
    totals: dict[str, int] = {}
    for key, value in entries:
        key_normalized = key.strip().lower()
        totals[key_normalized] = totals.get(key_normalized, 0) + value

    if totals:
        top_key = sorted(totals.items(), key=lambda item: (-item[1], item[0]))[0][0]
        top_value = totals[top_key]
    else:
        top_key = None
        top_value = None

    return {
        "total": sum(totals.values()),
        "unique_keys": len(totals),
        "top_key": top_key,
        "top_value": top_value,
    }


def _generate_string_regex_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    marker = MARKERS[idx % len(MARKERS)]
    min_len = 2 + (idx % 3)
    w1, w2, w3, w4 = _pick_words(rng, 4)
    token_a = f"{w1}_{idx % 10}"
    token_b = f"{w2}{idx % 7}"
    token_c = f"{w3}{(idx + 3) % 7}"
    token_d = f"{w4}_{(idx + 5) % 10}"
    short = "x" * max(1, min_len - 1)

    text1 = (
        f"Kickoff {marker}{token_a} then {marker}{token_b}! repeat {marker}{token_a.upper()} "
        f"and punctuation {marker}{token_b},"
    )
    text2 = (
        f"embedded{marker}{token_c} should be ignored; keep ({marker}{token_c}) and skip {marker}{short}."
    )
    text3 = f"Noise ({marker}{token_d}) plus {marker}{token_a}. trailing {marker}{token_d},"

    files = {
        "prompt.md": dedent(
            f"""
            # Task: Marker Extraction ({difficulty})

            Fix `extract_markers` in `src/solution.py`.

            A marker is `{marker}` followed by one or more characters from `[A-Za-z0-9_]`.

            Requirements:
            - Normalize tokens to lowercase.
            - Ignore tokens shorter than `MIN_LEN` ({min_len}).
            - Ignore tokens when the marker is embedded inside an identifier (the previous character is alphanumeric or underscore).
            - Deduplicate while preserving first-seen order.
            - Keep the function signature unchanged.

            Example:
            - Input: `... {marker}Alpha_1 ... {marker}alpha_1 ...`
            - Output: `["alpha_1"]`
            """
        ).strip()
        + "\n",
        "src/__init__.py": "\n",
        "src/solution.py": dedent(
            f"""
            import re

            MARKER = {marker!r}
            MIN_LEN = {min_len}


            def extract_markers(text: str) -> list[str]:
                # Buggy starter: captures obvious matches but ignores edge rules.
                pattern = re.compile(rf"{{re.escape(MARKER)}}([A-Za-z0-9_]+)")
                return [match.group(1) for match in pattern.finditer(text)]
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            from src.solution import extract_markers


            def test_normalizes_and_dedupes() -> None:
                text = {text1!r}
                assert extract_markers(text) == {[token_a.lower(), token_b.lower()]!r}


            def test_ignores_embedded_and_too_short_tokens() -> None:
                text = {text2!r}
                assert extract_markers(text) == {[token_c.lower()]!r}


            def test_preserves_order() -> None:
                text = {text3!r}
                assert extract_markers(text) == {[token_d.lower(), token_a.lower()]!r}
            """
        ).strip()
        + "\n",
    }

    return GeneratedTask(
        task_id=task_id,
        title=f"Extract markers {idx:03d}",
        category="string_regex_parsing",
        difficulty=difficulty,
        files=files,
    )


def _generate_ds_algo_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    a, b, c, d, e = _pick_words(rng, 5)

    records_main = [
        (a, 5 + (idx % 3)),
        (b, 2),
        (a, 1),
        (c, 9 + (idx % 2)),
        (b, -1),
        (d, 0),
        (e, -4),
    ]
    records_tie = [
        (a, 4),
        (d, 4),
        (e, 4),
        (a, -1),
        (d, -1),
        (b, 1),
    ]

    files = {
        "prompt.md": dedent(
            f"""
            # Task: Rank Products ({difficulty})

            Fix `rank_products(records, k)` in `src/solution.py`.

            `records` is a list of `(name, score_delta)` pairs.

            Requirements:
            - Aggregate score deltas by product name.
            - Drop products with total score `<= 0`.
            - Sort by total descending, then by product name ascending.
            - Return only product names.
            - Return at most `k` entries.
            - If `k <= 0`, return `[]`.
            """
        ).strip()
        + "\n",
        "src/__init__.py": "\n",
        "src/solution.py": dedent(
            """
            def rank_products(records: list[tuple[str, int]], k: int) -> list[str]:
                if k <= 0:
                    return []

                # Buggy starter: no aggregation and wrong ordering behavior.
                ordered = sorted(records, key=lambda item: (item[1], item[0]), reverse=True)
                return [name for name, _ in ordered[:k]]
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            from src.solution import rank_products


            def test_aggregates_and_sorts() -> None:
                records = {records_main!r}
                assert rank_products(records, 3) == {_rank_expected(records_main, 3)!r}


            def test_tie_breaks_alphabetically() -> None:
                records = {records_tie!r}
                assert rank_products(records, 2) == {_rank_expected(records_tie, 2)!r}


            def test_non_positive_k_returns_empty() -> None:
                records = {records_main!r}
                assert rank_products(records, 0) == []
            """
        ).strip()
        + "\n",
    }

    return GeneratedTask(
        task_id=task_id,
        title=f"Rank products {idx:03d}",
        category="ds_algo",
        difficulty=difficulty,
        files=files,
    )


def _generate_file_io_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    u1, u2, u3 = [word.lower() for word in _pick_words(rng, 3)]
    c1, c2, c3 = [word.lower() for word in _pick_words(rng, 3)]

    rows = [
        (u1, str(5 + idx % 4), c1),
        (u2, "3", c2),
        (u1, "2", c3),
        (u2, "oops", c1),
        (u3, "9", c1),
        ("", "4", c2),
        (u2, "7", c2),
    ]

    csv_lines = ["user,amount,category"]
    for user, amount, category in rows:
        csv_lines.append(f" {user} , {amount} , {category} ")
    csv_text = "\\n".join(csv_lines) + "\\n"
    expected = _summarize_rows(rows)

    files = {
        "prompt.md": dedent(
            f"""
            # Task: CSV -> JSON Summary ({difficulty})

            Fix `summarize_transactions(input_csv, output_json)` in `src/solution.py`.

            Input CSV columns: `user,amount,category`.

            Requirements:
            - Trim whitespace around all fields.
            - Ignore rows with empty user names.
            - Ignore rows where `amount` is not an integer.
            - Aggregate per user:
              - `total`: sum of amounts
              - `count`: number of valid rows
              - `categories`: sorted unique category names
            - Write JSON object keyed by user (sorted lexicographically).
            """
        ).strip()
        + "\n",
        "src/__init__.py": "\n",
        "src/solution.py": dedent(
            """
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
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            import json

            from src.solution import summarize_transactions


            def test_aggregates_valid_rows(tmp_path) -> None:
                input_path = tmp_path / "in.csv"
                output_path = tmp_path / "out.json"
                input_path.write_text({csv_text!r}, encoding="utf-8")

                summarize_transactions(str(input_path), str(output_path))
                payload = json.loads(output_path.read_text(encoding="utf-8"))

                assert payload == {expected!r}
                assert list(payload) == sorted(payload)


            def test_empty_input_produces_empty_object(tmp_path) -> None:
                input_path = tmp_path / "in.csv"
                output_path = tmp_path / "out.json"
                input_path.write_text("user,amount,category\\n", encoding="utf-8")

                summarize_transactions(str(input_path), str(output_path))
                payload = json.loads(output_path.read_text(encoding="utf-8"))
                assert payload == {{}}
            """
        ).strip()
        + "\n",
    }

    return GeneratedTask(
        task_id=task_id,
        title=f"CSV summary {idx:03d}",
        category="file_io_serialization",
        difficulty=difficulty,
        files=files,
    )


def _generate_concurrency_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    _ = rng
    delay = round(0.022 + (idx % 3) * 0.004, 3)
    job_count = 8 + (idx % 3)
    threshold = round(delay * job_count * 0.78, 3)

    files = {
        "prompt.md": dedent(
            f"""
            # Task: Concurrent Job Runner ({difficulty})

            Fix `run_jobs(jobs, max_workers)` in `src/solution.py`.

            Requirements:
            - Execute jobs concurrently (threading is acceptable).
            - Preserve input order in the returned list.
            - Raise `ValueError` if `max_workers <= 0`.
            - Propagate job exceptions.
            """
        ).strip()
        + "\n",
        "src/__init__.py": "\n",
        "src/solution.py": dedent(
            """
            from collections.abc import Callable


            def run_jobs(jobs: list[Callable[[], int]], max_workers: int) -> list[int]:
                if max_workers <= 0:
                    raise ValueError("max_workers must be > 0")

                # Buggy starter: executes sequentially.
                return [job() for job in jobs]
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            import time

            import pytest

            from src.solution import run_jobs


            def _make_job(value: int, delay: float):
                def _job() -> int:
                    time.sleep(delay)
                    return value

                return _job


            def test_parallel_execution_is_faster_than_sequential() -> None:
                jobs = [_make_job(i, {delay}) for i in range({job_count})]
                start = time.perf_counter()
                result = run_jobs(jobs, max_workers=4)
                elapsed = time.perf_counter() - start

                assert result == list(range({job_count}))
                assert elapsed < {threshold}


            def test_invalid_max_workers_raises() -> None:
                with pytest.raises(ValueError):
                    run_jobs([], max_workers=0)


            def test_exceptions_are_propagated() -> None:
                def ok() -> int:
                    return 1

                def boom() -> int:
                    raise RuntimeError("boom")

                with pytest.raises(RuntimeError):
                    run_jobs([ok, boom], max_workers=2)
            """
        ).strip()
        + "\n",
    }

    return GeneratedTask(
        task_id=task_id,
        title=f"Concurrent jobs {idx:03d}",
        category="concurrency_basics",
        difficulty=difficulty,
        files=files,
    )


def _generate_numerical_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    base_values = [round(rng.uniform(-8.0, 18.0), 2) for _ in range(8)]
    outlier = round(80 + idx * 0.5, 2)
    values = base_values + [outlier, float("nan")]
    trim_ratio = [0.1, 0.2, 0.25][idx % 3]
    expected = _trimmed_mean_oracle(values, trim_ratio)

    files = {
        "prompt.md": dedent(
            f"""
            # Task: Trimmed Mean ({difficulty})

            Fix `trimmed_mean(values, trim_ratio)` in `src/solution.py`.

            Requirements:
            - `trim_ratio` must satisfy `0 <= trim_ratio < 0.5`, else raise `ValueError`.
            - Ignore `NaN` values.
            - Sort remaining values.
            - Trim `int(n * trim_ratio)` values from each end.
            - Raise `ValueError` if no values remain.
            - Return the arithmetic mean of the retained values.
            """
        ).strip()
        + "\n",
        "src/__init__.py": "\n",
        "src/solution.py": dedent(
            """
            def trimmed_mean(values: list[float], trim_ratio: float) -> float:
                if not values:
                    raise ValueError("values must not be empty")

                # Buggy starter: no NaN handling, no trimming, no ratio validation.
                return sum(values) / len(values)
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            import math

            import pytest

            from src.solution import trimmed_mean


            def _oracle(values: list[float], trim_ratio: float) -> float:
                if not 0 <= trim_ratio < 0.5:
                    raise ValueError("trim_ratio must be in [0, 0.5)")

                filtered = [value for value in values if value == value]
                if not filtered:
                    raise ValueError("no finite values")

                ordered = sorted(filtered)
                trim_count = int(len(ordered) * trim_ratio)
                kept = ordered[trim_count : len(ordered) - trim_count]
                if not kept:
                    raise ValueError("all values were trimmed")
                return sum(kept) / len(kept)


            def test_matches_oracle_for_mixed_values() -> None:
                values = {values!r}
                result = trimmed_mean(values, {trim_ratio})
                assert result == pytest.approx({expected}, rel=1e-9, abs=1e-9)
                assert result == pytest.approx(_oracle(values, {trim_ratio}), rel=1e-9, abs=1e-9)


            def test_invalid_trim_ratio_raises() -> None:
                with pytest.raises(ValueError):
                    trimmed_mean([1.0, 2.0, 3.0], 0.5)


            def test_all_nan_raises() -> None:
                with pytest.raises(ValueError):
                    trimmed_mean([math.nan, math.nan], 0.1)
            """
        ).strip()
        + "\n",
    }

    return GeneratedTask(
        task_id=task_id,
        title=f"Trimmed mean {idx:03d}",
        category="numerical_edge_cases",
        difficulty=difficulty,
        files=files,
    )


def _generate_multi_file_task(task_id: str, idx: int, rng: random.Random, difficulty: str) -> GeneratedTask:
    k1, k2, k3 = [word.lower() for word in _pick_words(rng, 3)]
    separator = SEPARATORS[idx % len(SEPARATORS)]

    parsed_entries = [
        (k1, 4 + (idx % 3)),
        (k2, 2),
        (k1, 3),
        (k3, 6),
    ]
    expected = _mini_module_expected(parsed_entries)

    raw_lines = [
        f"{k1} {separator} {4 + (idx % 3)}",
        f"{k2}{separator}2",
        f"{k1}{separator}3",
        f"bad_line_without_separator",
        f"{k3}{separator}6",
        f"{k2}{separator}not_an_int",
        "",
    ]
    raw_blob = "\\n".join(raw_lines)

    files = {
        "prompt.md": dedent(
            f"""
            # Task: Mini Module Pipeline ({difficulty})

            This task spans multiple files under `src/`.

            Fix the mini-module so `summarize(raw: str)` in `src/pipeline.py` returns a stable report.

            Rules:
            - Use separator `{separator}`.
            - Ignore malformed lines and non-integer values.
            - Normalize keys to lowercase.
            - Aggregate duplicate keys by summing values.
            - Return report with keys:
              - `total`
              - `unique_keys`
              - `top_key` (highest value, tie -> lexicographically smallest key)
              - `top_value`
            """
        ).strip()
        + "\n",
        "src/__init__.py": dedent(
            """
            from .pipeline import summarize

            __all__ = ["summarize"]
            """
        ).strip()
        + "\n",
        "src/parser.py": dedent(
            f"""
            SEPARATOR = {separator!r}


            def parse_entries(raw: str, separator: str = SEPARATOR) -> list[tuple[str, int]]:
                entries: list[tuple[str, int]] = []
                for line in raw.splitlines():
                    if not line.strip():
                        continue
                    key, value = line.split(separator)
                    entries.append((key.strip(), int(value)))
                return entries
            """
        ).strip()
        + "\n",
        "src/aggregator.py": dedent(
            """
            def build_report(entries: list[tuple[str, int]]) -> dict[str, object]:
                total = 0
                keys: list[str] = []
                values: list[int] = []
                for key, value in entries:
                    total += value
                    keys.append(key)
                    values.append(value)

                return {
                    "total": total,
                    "unique_keys": len(set(keys)),
                    "top_key": keys[-1] if keys else None,
                    "top_value": values[-1] if values else None,
                }
            """
        ).strip()
        + "\n",
        "src/pipeline.py": dedent(
            """
            from .aggregator import build_report
            from .parser import parse_entries


            def summarize(raw: str) -> dict[str, object]:
                entries = parse_entries(raw)
                return build_report(entries)
            """
        ).strip()
        + "\n",
        "tests/test_solution.py": dedent(
            f"""
            from src.pipeline import summarize


            def test_pipeline_summary_handles_invalid_lines() -> None:
                raw = {raw_blob!r}
                assert summarize(raw) == {expected!r}


            def test_empty_input() -> None:
                assert summarize("") == {{
                    "total": 0,
                    "unique_keys": 0,
                    "top_key": None,
                    "top_value": None,
                }}
            """
        ).strip()
        + "\n",
    }

    return GeneratedTask(
        task_id=task_id,
        title=f"Mini module pipeline {idx:03d}",
        category="multi_file_mini_module",
        difficulty=difficulty,
        files=files,
    )


GeneratorFn = Callable[[str, int, random.Random, str], GeneratedTask]


CATEGORY_GENERATORS: dict[str, GeneratorFn] = {
    "string_regex_parsing": _generate_string_regex_task,
    "ds_algo": _generate_ds_algo_task,
    "file_io_serialization": _generate_file_io_task,
    "concurrency_basics": _generate_concurrency_task,
    "numerical_edge_cases": _generate_numerical_task,
    "multi_file_mini_module": _generate_multi_file_task,
}


def _task_index_from_id(task_id: str) -> int:
    try:
        suffix = task_id.rsplit("_", 1)[1]
        return int(suffix)
    except (IndexError, ValueError) as exc:
        raise ValueError(f"Invalid task id format: {task_id}") from exc


def generate_task_variant(
    *,
    task_id: str,
    category: str,
    difficulty: str,
    seed: int = DEFAULT_SEED,
    variant: int = 0,
    strict_level: int = 0,
) -> GeneratedTask:
    if category not in CATEGORY_GENERATORS:
        known = ", ".join(sorted(CATEGORY_GENERATORS))
        raise ValueError(f"Unknown category `{category}`. Known categories: {known}")

    task_index = _task_index_from_id(task_id)
    category_index = CATEGORY_ORDER.index(category)
    rng = random.Random(_task_seed(seed, category_index, task_index, variant=variant))
    generator = CATEGORY_GENERATORS[category]
    generated = generator(task_id, task_index, rng, difficulty)
    return _apply_quality_profile(generated, strict_level=strict_level)


def _build_task_list(seed: int) -> list[GeneratedTask]:
    generated: list[GeneratedTask] = []
    for category_index, category in enumerate(CATEGORY_ORDER):
        for task_index in range(TASKS_PER_CATEGORY):
            task_id = f"v1_{category}_{task_index:03d}"
            difficulty = DIFFICULTIES[(task_index + category_index) % len(DIFFICULTIES)]
            generated.append(
                generate_task_variant(
                    task_id=task_id,
                    category=category,
                    difficulty=difficulty,
                    seed=seed,
                    variant=0,
                    strict_level=0,
                )
            )
    return generated


def _assign_splits(task_ids: list[str], seed: int) -> dict[str, str]:
    shuffled = list(task_ids)
    random.Random(seed).shuffle(shuffled)

    split_map: dict[str, str] = {}
    for idx, task_id in enumerate(shuffled):
        if idx < 200:
            split_map[task_id] = "train"
        elif idx < 250:
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
        category_rng = random.Random(seed + 5000 + category_index * 37)
        category_rng.shuffle(candidates)
        quick_ids.update(candidates[:3])

    return quick_ids


def _write_task_files(base: Path, task: GeneratedTask) -> None:
    task_dir = base / "tasks" / task.task_id
    for rel_path, content in task.files.items():
        path = task_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def write_task_variant(base: Path, task: GeneratedTask, *, clean: bool = True) -> None:
    task_dir = base / "tasks" / task.task_id
    if clean and task_dir.exists():
        shutil.rmtree(task_dir)
    _write_task_files(base, task)


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

    tasks = _build_task_list(seed=seed)
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

    if counts != {"total": 300, "train": 200, "dev": 50, "test": 50, "quick": 18}:
        raise RuntimeError(f"Unexpected split counts: {counts}")

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

    metadata_path = root / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate task_pack_v1 benchmark tasks.")
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
