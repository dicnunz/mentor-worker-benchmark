from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.runner import BenchmarkConfig, run_benchmark
from mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack import (
    CATEGORY_ORDER,
    generate_task_variant,
    write_task_variant,
)
from mentor_worker_benchmark.tasks.task_pack_v1.validate import validate_task_pack

TARGET_DIFFICULTY_RATIO = {"easy": 0.35, "medium": 0.45, "hard": 0.20}
CALIBRATION_MODELS = ("phi3:mini", "qwen2.5-coder:7b")
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass(slots=True)
class CurationConfig:
    task_pack: str = "task_pack_v1"
    seed: int = 1337
    similarity_threshold: float = 0.92
    triviality_sample_size: int = 72
    full_triviality_model_check: bool = False
    max_replacement_attempts: int = 10
    results_dir: Path = Path("results")
    worker_num_predict: int = 220
    ollama_timeout_seconds: int = 60


@dataclass(slots=True)
class TaskEntry:
    task_id: str
    title: str
    category: str
    difficulty: str
    split: str
    quick: bool
    path: Path
    prompt: str
    tests: str
    starter: str
    metadata_row: dict[str, Any]


@dataclass(slots=True)
class TaskHeuristics:
    test_count: int
    starter_line_count: int
    has_io_examples: bool
    has_boundary_tests: bool
    has_invalid_input_tests: bool


@dataclass(slots=True)
class CalibrationResult:
    model: str
    pass_rate: float
    pass_by_task: dict[str, bool]
    runs: int
    status: str


def _pack_root() -> Path:
    return Path(__file__).resolve().parent


def _metadata_path() -> Path:
    return _pack_root() / "metadata.json"


def _read_metadata() -> dict[str, Any]:
    path = _metadata_path()
    if not path.exists():
        raise RuntimeError(f"Missing metadata.json at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_metadata(payload: dict[str, Any]) -> None:
    _metadata_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_entries(metadata: dict[str, Any]) -> dict[str, TaskEntry]:
    entries: dict[str, TaskEntry] = {}
    root = _pack_root()
    for row in metadata.get("tasks", []):
        if not isinstance(row, dict):
            continue
        task_id = str(row["task_id"])
        task_path = (root / str(row["path"])).resolve()
        prompt_path = task_path / "prompt.md"
        tests_path = task_path / "tests" / "test_solution.py"
        src_dir = task_path / "src"
        starter_parts: list[str] = []
        for src_file in sorted(src_dir.glob("*.py")):
            if src_file.name == "__init__.py":
                continue
            starter_parts.append(src_file.read_text(encoding="utf-8"))
        entries[task_id] = TaskEntry(
            task_id=task_id,
            title=str(row["title"]),
            category=str(row["category"]),
            difficulty=str(row["difficulty"]),
            split=str(row["split"]),
            quick=bool(row.get("quick", False)),
            path=task_path,
            prompt=prompt_path.read_text(encoding="utf-8"),
            tests=tests_path.read_text(encoding="utf-8"),
            starter="\n\n".join(starter_parts),
            metadata_row=row,
        )
    return entries


def _difficulty_distribution(entries: dict[str, TaskEntry]) -> dict[str, int]:
    dist = {"easy": 0, "medium": 0, "hard": 0}
    for entry in entries.values():
        if entry.difficulty not in dist:
            continue
        dist[entry.difficulty] += 1
    return dist


def _target_difficulty_counts(total: int) -> dict[str, int]:
    easy = int(round(total * TARGET_DIFFICULTY_RATIO["easy"]))
    medium = int(round(total * TARGET_DIFFICULTY_RATIO["medium"]))
    hard = total - easy - medium
    return {"easy": easy, "medium": medium, "hard": hard}


def _task_quality(entry: TaskEntry) -> TaskHeuristics:
    test_count = len(re.findall(r"^def\s+test_", entry.tests, flags=re.MULTILINE))
    starter_lines = [
        line
        for line in entry.starter.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    has_example_kw = bool(re.search(r"\bexample\b", entry.prompt, flags=re.IGNORECASE))
    has_input_kw = bool(re.search(r"\binput\b", entry.prompt, flags=re.IGNORECASE))
    has_output_kw = bool(re.search(r"\boutput\b", entry.prompt, flags=re.IGNORECASE))
    has_io_examples = has_example_kw and has_input_kw and has_output_kw

    boundary_patterns = [
        r"\"\"",
        r"\[\]",
        r"\{\}",
        r"\b0\b",
        r"-1",
        r"\bNone\b",
        r"\bnan\b",
        r"\bempty\b",
        r"\bboundary\b",
    ]
    has_boundary = any(re.search(pattern, entry.tests, flags=re.IGNORECASE) for pattern in boundary_patterns)
    has_invalid = bool(
        re.search(
            r"pytest\.raises|ValueError|TypeError|RuntimeError|invalid|malformed",
            entry.tests,
            flags=re.IGNORECASE,
        )
    )

    return TaskHeuristics(
        test_count=test_count,
        starter_line_count=len(starter_lines),
        has_io_examples=has_io_examples,
        has_boundary_tests=has_boundary,
        has_invalid_input_tests=has_invalid,
    )


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _hash_bucket(payload: str, buckets: int) -> int:
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % buckets


def _hashed_ngram_vector(text: str, *, token_n: int = 3, buckets: int = 2048) -> dict[int, float]:
    tokens = _tokenize(text)
    vector: dict[int, float] = {}

    if len(tokens) >= token_n:
        for idx in range(len(tokens) - token_n + 1):
            gram = " ".join(tokens[idx : idx + token_n])
            bucket = _hash_bucket(f"tok:{gram}", buckets)
            vector[bucket] = vector.get(bucket, 0.0) + 1.0
    else:
        for token in tokens:
            bucket = _hash_bucket(f"tok:{token}", buckets)
            vector[bucket] = vector.get(bucket, 0.0) + 1.0

    compact = re.sub(r"\s+", " ", text.lower())
    if len(compact) >= 5:
        for idx in range(len(compact) - 4):
            shingle = compact[idx : idx + 5]
            bucket = _hash_bucket(f"char:{shingle}", buckets)
            vector[bucket] = vector.get(bucket, 0.0) + 0.35

    return vector


def _cosine_similarity(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    dot = 0.0
    for key, value in left.items():
        dot += value * right.get(key, 0.0)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a: str, b: str) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return
        if root_a < root_b:
            self.parent[root_b] = root_a
        else:
            self.parent[root_a] = root_b


def _pairwise_duplicates(
    entries: dict[str, TaskEntry],
    *,
    similarity_threshold: float,
) -> tuple[list[list[str]], dict[tuple[str, str], float], dict[str, dict[int, float]]]:
    task_ids = sorted(entries)
    vectors = {
        task_id: _hashed_ngram_vector(entries[task_id].prompt + "\n" + entries[task_id].tests)
        for task_id in task_ids
    }
    pair_scores: dict[tuple[str, str], float] = {}
    union_find = _UnionFind(task_ids)

    for idx, left in enumerate(task_ids):
        for right in task_ids[idx + 1 :]:
            score = _cosine_similarity(vectors[left], vectors[right])
            if score >= similarity_threshold:
                union_find.union(left, right)
                pair_scores[(left, right)] = score

    clusters_by_root: dict[str, list[str]] = defaultdict(list)
    for task_id in task_ids:
        clusters_by_root[union_find.find(task_id)].append(task_id)

    clusters = [sorted(cluster) for cluster in clusters_by_root.values() if len(cluster) > 1]
    clusters.sort(key=lambda group: (-len(group), group[0]))
    return clusters, pair_scores, vectors


def _cluster_average_similarity(cluster: list[str], pair_scores: dict[tuple[str, str], float]) -> float:
    scores: list[float] = []
    for idx, left in enumerate(cluster):
        for right in cluster[idx + 1 :]:
            key = (left, right) if left < right else (right, left)
            if key in pair_scores:
                scores.append(pair_scores[key])
    return mean(scores) if scores else 0.0


def _quality_score(entry: TaskEntry, heuristics: TaskHeuristics) -> float:
    score = 0.0
    score += heuristics.test_count * 10
    score += heuristics.starter_line_count * 2
    score += len(_tokenize(entry.prompt)) * 0.1
    if heuristics.has_io_examples:
        score += 8
    if heuristics.has_boundary_tests:
        score += 6
    if heuristics.has_invalid_input_tests:
        score += 6
    return score


def _pick_duplicate_replacements(
    clusters: list[list[str]],
    entries: dict[str, TaskEntry],
    heuristics: dict[str, TaskHeuristics],
) -> tuple[set[str], list[dict[str, Any]]]:
    duplicates: set[str] = set()
    cluster_rows: list[dict[str, Any]] = []
    for cluster_index, cluster in enumerate(clusters, start=1):
        ranked = sorted(
            cluster,
            key=lambda task_id: (-_quality_score(entries[task_id], heuristics[task_id]), task_id),
        )
        keeper = ranked[0]
        replaced = ranked[1:]
        duplicates.update(replaced)
        cluster_rows.append(
            {
                "cluster_id": cluster_index,
                "size": len(cluster),
                "keeper": keeper,
                "members": cluster,
                "replaced_members": replaced,
            }
        )
    return duplicates, cluster_rows


def _stable_sample(ids: list[str], n: int, seed: int) -> list[str]:
    if n >= len(ids):
        return sorted(ids)
    ordered = sorted(ids)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    return sorted(ordered[:n])


def _balanced_category_sample(entries: dict[str, TaskEntry], *, sample_size: int, seed: int) -> list[str]:
    if sample_size >= len(entries):
        return sorted(entries)

    by_category: dict[str, list[str]] = defaultdict(list)
    for task_id, entry in entries.items():
        by_category[entry.category].append(task_id)
    for ids in by_category.values():
        ids.sort()

    per_category = max(1, sample_size // max(1, len(by_category)))
    picked: set[str] = set()

    for category_index, category in enumerate(CATEGORY_ORDER):
        category_ids = by_category.get(category, [])
        if not category_ids:
            continue
        seeded = _stable_sample(category_ids, min(per_category, len(category_ids)), seed + 100 * category_index)
        picked.update(seeded)

    if len(picked) < sample_size:
        remaining = sorted(set(entries) - picked)
        refill = _stable_sample(remaining, sample_size - len(picked), seed + 9999)
        picked.update(refill)

    return sorted(picked)


def _run_worker_only(
    *,
    task_pack: str,
    seed: int,
    model: str,
    suite: str | None = None,
    task_ids: list[str] | None = None,
    client: OllamaClient,
    results_path: Path,
    worker_num_predict: int,
) -> CalibrationResult:
    selector = ",".join(task_ids) if task_ids else None
    config = BenchmarkConfig(
        models=[model],
        max_turns=1,
        task_pack=task_pack,
        suite=suite,
        task_selector=selector,
        seed=seed,
        results_path=results_path,
        run_modes=("worker_only",),
        repro_mode=False,
        worker_num_predict_override=worker_num_predict,
    )
    payload = run_benchmark(config, client=client)
    worker_runs = [run for run in payload.get("runs", []) if run.get("mode") == "worker_only"]
    pass_by_task = {str(run["task_id"]): bool(run.get("pass")) for run in worker_runs}
    pass_rate = mean(1.0 if value else 0.0 for value in pass_by_task.values()) if pass_by_task else 0.0
    return CalibrationResult(
        model=model,
        pass_rate=pass_rate,
        pass_by_task=pass_by_task,
        runs=len(worker_runs),
        status="ok",
    )


def _ensure_ollama(client: OllamaClient, required_models: list[str]) -> None:
    status = client.ensure_server_running(auto_start=False)
    if not status.reachable:
        raise RuntimeError(
            f"{status.message} Curation requires local model calibration. "
            "Start Ollama (`ollama serve`) and retry."
        )
    local_models = client.list_local_models()
    missing = [model for model in required_models if model not in local_models]
    if missing:
        missing_label = ", ".join(missing)
        raise RuntimeError(
            f"Curation requires local models {missing_label}. "
            "Run `python -m mentor_worker_benchmark setup` first."
        )


def _dev_ease_scores(
    entries: dict[str, TaskEntry],
    calibration_by_model: dict[str, CalibrationResult],
) -> tuple[dict[str, float], dict[tuple[str, str], float], dict[str, float]]:
    per_task: dict[str, float] = {}
    bucket_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    category_scores: dict[str, list[float]] = defaultdict(list)

    for task_id, entry in entries.items():
        if entry.split != "dev":
            continue
        values = [
            1.0 if result.pass_by_task.get(task_id, False) else 0.0
            for result in calibration_by_model.values()
            if result.status == "ok"
        ]
        if not values:
            continue
        task_score = mean(values)
        per_task[task_id] = task_score
        bucket_scores[(entry.category, entry.difficulty)].append(task_score)
        category_scores[entry.category].append(task_score)

    bucket_avg = {key: mean(values) for key, values in bucket_scores.items() if values}
    category_avg = {key: mean(values) for key, values in category_scores.items() if values}
    return per_task, bucket_avg, category_avg


def _assign_difficulties(
    entries: dict[str, TaskEntry],
    *,
    seed: int,
    dev_task_scores: dict[str, float],
    bucket_avg: dict[tuple[str, str], float],
    category_avg: dict[str, float],
) -> dict[str, str]:
    target = _target_difficulty_counts(len(entries))
    global_avg = mean(dev_task_scores.values()) if dev_task_scores else 0.0

    scored: list[tuple[float, str]] = []
    for task_id, entry in entries.items():
        ease = dev_task_scores.get(task_id)
        if ease is None:
            ease = bucket_avg.get((entry.category, entry.difficulty))
        if ease is None:
            ease = category_avg.get(entry.category, global_avg)

        # Add tiny deterministic jitter for stable tie breaks.
        digest = hashlib.sha256(f"{seed}:{task_id}".encode("utf-8")).hexdigest()
        jitter = int(digest[:6], 16) / float(0xFFFFFF) * 1e-4
        scored.append((ease + jitter, task_id))

    scored.sort(key=lambda item: (-item[0], item[1]))

    assigned: dict[str, str] = {}
    easy_cut = target["easy"]
    medium_cut = target["easy"] + target["medium"]
    for idx, (_, task_id) in enumerate(scored):
        if idx < easy_cut:
            assigned[task_id] = "easy"
        elif idx < medium_cut:
            assigned[task_id] = "medium"
        else:
            assigned[task_id] = "hard"
    return assigned


def _bucket_adjustments(
    entries: dict[str, TaskEntry],
    dev_task_scores: dict[str, float],
) -> dict[tuple[str, str], int]:
    targets = {
        "easy": (0.40, 0.90),
        "medium": (0.15, 0.60),
        "hard": (0.00, 0.30),
    }
    observed: dict[tuple[str, str], list[float]] = defaultdict(list)
    for task_id, score in dev_task_scores.items():
        entry = entries[task_id]
        observed[(entry.category, entry.difficulty)].append(score)

    adjustments: dict[tuple[str, str], int] = {}
    for (category, difficulty), values in observed.items():
        if len(values) < 2:
            continue
        low, high = targets[difficulty]
        rate = mean(values)
        if rate > high:
            adjustments[(category, difficulty)] = 1
        elif rate < low:
            adjustments[(category, difficulty)] = -1
        else:
            adjustments[(category, difficulty)] = 0
    return adjustments


def _candidate_vector(task: TaskEntry) -> dict[int, float]:
    return _hashed_ngram_vector(task.prompt + "\n" + task.tests)


def _task_entry_from_generated(
    generated: Any,
    original: TaskEntry,
) -> TaskEntry:
    prompt = str(generated.files["prompt.md"])
    tests = str(generated.files["tests/test_solution.py"])
    starter_parts: list[str] = []
    for rel, content in generated.files.items():
        if rel.startswith("src/") and rel.endswith(".py") and not rel.endswith("__init__.py"):
            starter_parts.append(content)
    starter = "\n\n".join(starter_parts)
    return TaskEntry(
        task_id=original.task_id,
        title=generated.title,
        category=original.category,
        difficulty=original.difficulty,
        split=original.split,
        quick=original.quick,
        path=original.path,
        prompt=prompt,
        tests=tests,
        starter=starter,
        metadata_row=original.metadata_row,
    )


def _replacement_strict_level(
    *,
    reasons: set[str],
    target_difficulty: str,
    bucket_adjustment: int,
) -> int:
    strict_level = 1
    if "duplicate_near" in reasons:
        strict_level += 1
    if "ambiguous_prompt" in reasons or "ambiguous_tests" in reasons:
        strict_level += 1
    if "trivial_model_pass" in reasons:
        strict_level += 1
    if target_difficulty == "hard":
        strict_level += 1
    if bucket_adjustment > 0:
        strict_level += bucket_adjustment
    if bucket_adjustment < 0:
        strict_level = max(0, strict_level - 1)
    return max(0, min(3, strict_level))


def _regenerate_flagged_tasks(
    *,
    entries: dict[str, TaskEntry],
    reasons_by_task: dict[str, set[str]],
    reassigned_difficulty: dict[str, str],
    bucket_adjustments: dict[tuple[str, str], int],
    vectors: dict[str, dict[int, float]],
    config: CurationConfig,
) -> dict[str, Any]:
    replaced = sorted(task_id for task_id, reasons in reasons_by_task.items() if reasons)
    if not replaced:
        return {"replaced_ids": [], "attempts_by_task": {}}

    accepted_vectors: list[tuple[str, dict[int, float]]] = []
    for task_id, vector in vectors.items():
        if task_id in reasons_by_task and reasons_by_task[task_id]:
            continue
        accepted_vectors.append((task_id, vector))

    attempts_by_task: dict[str, int] = {}
    root = _pack_root()

    for index, task_id in enumerate(replaced):
        entry = entries[task_id]
        reasons = reasons_by_task[task_id]
        target_difficulty = reassigned_difficulty.get(task_id, entry.difficulty)
        adjustment_key = (entry.category, target_difficulty)
        strict_level = _replacement_strict_level(
            reasons=reasons,
            target_difficulty=target_difficulty,
            bucket_adjustment=bucket_adjustments.get(adjustment_key, 0),
        )

        base_variant_digest = hashlib.sha256(f"{config.seed}:{task_id}".encode("utf-8")).hexdigest()
        base_variant = int(base_variant_digest[:8], 16)

        chosen = None
        chosen_entry = None
        attempts = 0
        for attempt in range(config.max_replacement_attempts):
            attempts = attempt + 1
            variant = base_variant + attempt + index * 17
            generated = generate_task_variant(
                task_id=task_id,
                category=entry.category,
                difficulty=target_difficulty,
                seed=config.seed,
                variant=variant,
                strict_level=strict_level,
            )
            candidate_entry = _task_entry_from_generated(generated, entry)
            quality = _task_quality(candidate_entry)
            if quality.test_count < 3:
                continue
            if not quality.has_io_examples:
                continue
            if not quality.has_boundary_tests or not quality.has_invalid_input_tests:
                continue

            candidate_vec = _candidate_vector(candidate_entry)
            max_sim = max(
                (_cosine_similarity(candidate_vec, vec) for _, vec in accepted_vectors),
                default=0.0,
            )
            if max_sim >= config.similarity_threshold:
                continue

            chosen = generated
            chosen_entry = candidate_entry
            accepted_vectors.append((task_id, candidate_vec))
            break

        if chosen is None:
            # Deterministic fallback: accept the last attempt even if still imperfect.
            fallback_variant = base_variant + config.max_replacement_attempts + index * 17
            chosen = generate_task_variant(
                task_id=task_id,
                category=entry.category,
                difficulty=target_difficulty,
                seed=config.seed,
                variant=fallback_variant,
                strict_level=max(2, strict_level),
            )
            chosen_entry = _task_entry_from_generated(chosen, entry)
            accepted_vectors.append((task_id, _candidate_vector(chosen_entry)))

        attempts_by_task[task_id] = attempts
        write_task_variant(root, chosen, clean=True)

        entry.metadata_row["title"] = chosen.title
        entry.metadata_row["difficulty"] = target_difficulty
        entry.title = chosen.title
        entry.difficulty = target_difficulty
        entry.prompt = chosen_entry.prompt
        entry.tests = chosen_entry.tests
        entry.starter = chosen_entry.starter

    return {"replaced_ids": replaced, "attempts_by_task": attempts_by_task}


def _refresh_metadata(metadata: dict[str, Any], entries: dict[str, TaskEntry]) -> None:
    tasks_rows = []
    for task_id in sorted(entries):
        row = entries[task_id].metadata_row
        tasks_rows.append(
            {
                "task_id": row["task_id"],
                "title": row["title"],
                "category": row["category"],
                "difficulty": row["difficulty"],
                "split": row["split"],
                "quick": row["quick"],
                "path": row["path"],
            }
        )

    counts = {
        "total": len(tasks_rows),
        "train": sum(1 for row in tasks_rows if row["split"] == "train"),
        "dev": sum(1 for row in tasks_rows if row["split"] == "dev"),
        "test": sum(1 for row in tasks_rows if row["split"] == "test"),
        "quick": sum(1 for row in tasks_rows if row["quick"]),
    }
    if counts != {"total": 300, "train": 200, "dev": 50, "test": 50, "quick": 18}:
        raise RuntimeError(f"Curation produced invalid split counts: {counts}")

    category_counts: dict[str, int] = {}
    for row in tasks_rows:
        category = str(row["category"])
        category_counts[category] = category_counts.get(category, 0) + 1

    metadata["pack_version"] = "1.1.0"
    metadata["generator_seed"] = int(metadata.get("generator_seed", 0))
    metadata["tasks"] = tasks_rows
    metadata["counts"] = counts
    metadata["category_counts"] = category_counts


def _model_summary(calibration: dict[str, CalibrationResult]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for model, result in calibration.items():
        summary[model] = {
            "status": result.status,
            "runs": result.runs,
            "pass_rate": round(result.pass_rate, 4),
        }
    ok_rates = [result.pass_rate for result in calibration.values() if result.status == "ok"]
    summary["average_pass_rate"] = round(mean(ok_rates), 4) if ok_rates else None
    return summary


def _render_markdown_report(payload: dict[str, Any]) -> str:
    before_dist = payload["difficulty_distribution"]["before"]
    after_dist = payload["difficulty_distribution"]["after"]
    replaced = payload["replacements"]["count"]
    clusters = payload["duplicates"]["top_clusters"]
    before_cal = payload["dev_calibration"]["before_summary"]
    after_cal = payload["dev_calibration"]["after_summary"]
    flagged_counts = payload["flagged_reason_counts"]

    lines = [
        "# Task Pack Curation Report",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "## Summary",
        f"- Task pack: `{payload['task_pack']}`",
        f"- Replaced tasks: **{replaced}**",
        f"- Near-duplicate clusters (before): **{payload['duplicates']['cluster_count_before']}**",
        f"- Near-duplicate clusters (after): **{payload['duplicates']['cluster_count_after']}**",
        "",
        "## Difficulty Distribution",
        "",
        "| Bucket | Before | After |",
        "| --- | --- | --- |",
        f"| easy | {before_dist.get('easy', 0)} | {after_dist.get('easy', 0)} |",
        f"| medium | {before_dist.get('medium', 0)} | {after_dist.get('medium', 0)} |",
        f"| hard | {before_dist.get('hard', 0)} | {after_dist.get('hard', 0)} |",
        "",
        "## DEV Baseline Pass Rate (1-turn worker_only)",
        "",
        "| Model | Before | After |",
        "| --- | --- | --- |",
        f"| phi3:mini | {before_cal.get('phi3:mini', {}).get('pass_rate', 'n/a')} | {after_cal.get('phi3:mini', {}).get('pass_rate', 'n/a')} |",
        f"| qwen2.5-coder:7b | {before_cal.get('qwen2.5-coder:7b', {}).get('pass_rate', 'n/a')} | {after_cal.get('qwen2.5-coder:7b', {}).get('pass_rate', 'n/a')} |",
        f"| average | {before_cal.get('average_pass_rate', 'n/a')} | {after_cal.get('average_pass_rate', 'n/a')} |",
        "",
        "## Flagged Reason Counts",
        "",
    ]

    for key in sorted(flagged_counts):
        lines.append(f"- `{key}`: {flagged_counts[key]}")

    lines.extend(["", "## Top Duplicate Clusters (Before)", ""])
    if clusters:
        lines.append("| Cluster | Size | Keeper | Members |")
        lines.append("| --- | --- | --- | --- |")
        for row in clusters:
            members = ", ".join(row["members"][:6])
            if len(row["members"]) > 6:
                members += ", ..."
            lines.append(f"| {row['cluster_id']} | {row['size']} | `{row['keeper']}` | {members} |")
    else:
        lines.append("- No near-duplicate clusters detected.")

    return "\n".join(lines).rstrip() + "\n"


def run_curation(config: CurationConfig) -> dict[str, Any]:
    if config.task_pack != "task_pack_v1":
        raise ValueError("`curate` currently supports only --task-pack task_pack_v1.")

    print("Loading task pack metadata and computing quality heuristics...")
    metadata = _read_metadata()
    entries = _load_entries(metadata)
    before_dist = _difficulty_distribution(entries)

    heuristics_by_task = {task_id: _task_quality(entry) for task_id, entry in entries.items()}
    duplicate_clusters, pair_scores, vectors = _pairwise_duplicates(
        entries, similarity_threshold=config.similarity_threshold
    )
    duplicate_ids, cluster_rows = _pick_duplicate_replacements(
        duplicate_clusters, entries=entries, heuristics=heuristics_by_task
    )

    reasons_by_task: dict[str, set[str]] = defaultdict(set)
    for task_id in duplicate_ids:
        reasons_by_task[task_id].add("duplicate_near")

    for task_id, quality in heuristics_by_task.items():
        if quality.test_count < 3:
            reasons_by_task[task_id].add("trivial_low_test_count")
        if quality.starter_line_count < 8:
            reasons_by_task[task_id].add("trivial_short_starter")
        if not quality.has_io_examples:
            reasons_by_task[task_id].add("ambiguous_prompt")
        if not quality.has_boundary_tests or not quality.has_invalid_input_tests:
            reasons_by_task[task_id].add("ambiguous_tests")

    client = OllamaClient(timeout_seconds=config.ollama_timeout_seconds)
    _ensure_ollama(client, list(CALIBRATION_MODELS))

    tmp_dir = config.results_dir / "_curation_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print("Running phi3 triviality probe (worker_only, 1 turn)...")
    trivial_sample_ids = (
        sorted(entries)
        if config.full_triviality_model_check
        else _balanced_category_sample(
            entries,
            sample_size=max(1, min(config.triviality_sample_size, len(entries))),
            seed=config.seed,
        )
    )
    trivial_eval = _run_worker_only(
        task_pack=config.task_pack,
        seed=config.seed + 3,
        model="phi3:mini",
        task_ids=trivial_sample_ids,
        client=client,
        results_path=tmp_dir / "triviality_phi3.json",
        worker_num_predict=config.worker_num_predict,
    )
    for task_id, passed in trivial_eval.pass_by_task.items():
        if passed:
            reasons_by_task[task_id].add("trivial_model_pass")

    print("Running DEV calibration (before) on phi3:mini and qwen2.5-coder:7b...")
    before_calibration: dict[str, CalibrationResult] = {}
    for model_index, model in enumerate(CALIBRATION_MODELS):
        before_calibration[model] = _run_worker_only(
            task_pack=config.task_pack,
            seed=config.seed + 101 + model_index,
            model=model,
            suite="dev",
            client=client,
            results_path=tmp_dir / f"dev_before_{model.replace(':', '_')}.json",
            worker_num_predict=config.worker_num_predict,
        )

    dev_scores, bucket_avg, category_avg = _dev_ease_scores(entries, before_calibration)
    reassigned_difficulty = _assign_difficulties(
        entries,
        seed=config.seed,
        dev_task_scores=dev_scores,
        bucket_avg=bucket_avg,
        category_avg=category_avg,
    )
    bucket_adjustments = _bucket_adjustments(entries, dev_scores)

    print("Regenerating flagged tasks with stricter deterministic variants...")
    for task_id, entry in entries.items():
        target_diff = reassigned_difficulty.get(task_id, entry.difficulty)
        if target_diff != entry.difficulty:
            reasons_by_task[task_id].add("difficulty_rebalanced")
        if bucket_adjustments.get((entry.category, target_diff), 0) != 0:
            reasons_by_task[task_id].add("calibration_bucket_adjustment")

    replacement_summary = _regenerate_flagged_tasks(
        entries=entries,
        reasons_by_task=reasons_by_task,
        reassigned_difficulty=reassigned_difficulty,
        bucket_adjustments=bucket_adjustments,
        vectors=vectors,
        config=config,
    )

    _refresh_metadata(metadata, entries)
    _write_metadata(metadata)

    print("Validating curated task pack...")
    ok, errors = validate_task_pack()
    if not ok:
        raise RuntimeError("Curation produced invalid task pack:\n" + "\n".join(errors))

    refreshed_entries = _load_entries(metadata)
    after_dist = _difficulty_distribution(refreshed_entries)
    after_clusters, after_pair_scores, _ = _pairwise_duplicates(
        refreshed_entries, similarity_threshold=config.similarity_threshold
    )

    print("Running DEV calibration (after) on phi3:mini and qwen2.5-coder:7b...")
    after_calibration: dict[str, CalibrationResult] = {}
    for model_index, model in enumerate(CALIBRATION_MODELS):
        after_calibration[model] = _run_worker_only(
            task_pack=config.task_pack,
            seed=config.seed + 201 + model_index,
            model=model,
            suite="dev",
            client=client,
            results_path=tmp_dir / f"dev_after_{model.replace(':', '_')}.json",
            worker_num_predict=config.worker_num_predict,
        )

    flagged_reason_counts: dict[str, int] = defaultdict(int)
    for reasons in reasons_by_task.values():
        for reason in reasons:
            flagged_reason_counts[reason] += 1

    top_clusters: list[dict[str, Any]] = []
    for row in cluster_rows[:10]:
        average_similarity = _cluster_average_similarity(row["members"], pair_scores)
        top_clusters.append(
            {
                "cluster_id": row["cluster_id"],
                "size": row["size"],
                "keeper": row["keeper"],
                "members": row["members"],
                "average_similarity": round(average_similarity, 4),
            }
        )

    payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "task_pack": config.task_pack,
        "seed": config.seed,
        "config": {
            "similarity_threshold": config.similarity_threshold,
            "triviality_sample_size": len(trivial_sample_ids),
            "full_triviality_model_check": config.full_triviality_model_check,
            "max_replacement_attempts": config.max_replacement_attempts,
            "calibration_models": list(CALIBRATION_MODELS),
            "worker_num_predict": config.worker_num_predict,
            "ollama_timeout_seconds": config.ollama_timeout_seconds,
        },
        "replacements": {
            "count": len(replacement_summary["replaced_ids"]),
            "task_ids": replacement_summary["replaced_ids"],
            "attempts_by_task": replacement_summary["attempts_by_task"],
        },
        "duplicates": {
            "cluster_count_before": len(duplicate_clusters),
            "cluster_count_after": len(after_clusters),
            "top_clusters": top_clusters,
            "after_top_clusters": [
                {
                    "size": len(cluster),
                    "members": cluster,
                    "average_similarity": round(_cluster_average_similarity(cluster, after_pair_scores), 4),
                }
                for cluster in after_clusters[:10]
            ],
        },
        "difficulty_distribution": {
            "before": before_dist,
            "after": after_dist,
            "target": _target_difficulty_counts(len(entries)),
        },
        "triviality_model_check": {
            "model": trivial_eval.model,
            "sample_size": len(trivial_sample_ids),
            "pass_rate": round(trivial_eval.pass_rate, 4),
            "passed_task_ids": sorted(task_id for task_id, passed in trivial_eval.pass_by_task.items() if passed),
        },
        "flagged_reason_counts": dict(sorted(flagged_reason_counts.items())),
        "dev_calibration": {
            "before_summary": _model_summary(before_calibration),
            "after_summary": _model_summary(after_calibration),
        },
    }

    config.results_dir.mkdir(parents=True, exist_ok=True)
    report_json = config.results_dir / "curation_report.json"
    report_md = config.results_dir / "curation_report.md"
    report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_md.write_text(_render_markdown_report(payload), encoding="utf-8")
    print("Wrote curation reports.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate task_pack_v1 using quality gates and calibration.")
    parser.add_argument("--task-pack", default="task_pack_v1")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--similarity-threshold", type=float, default=0.92)
    parser.add_argument("--triviality-sample-size", type=int, default=72)
    parser.add_argument("--full-triviality-model-check", action="store_true")
    parser.add_argument("--max-replacement-attempts", type=int, default=10)
    parser.add_argument("--worker-num-predict", type=int, default=220)
    parser.add_argument("--ollama-timeout-seconds", type=int, default=60)
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()

    payload = run_curation(
        CurationConfig(
            task_pack=args.task_pack,
            seed=args.seed,
            similarity_threshold=args.similarity_threshold,
            triviality_sample_size=args.triviality_sample_size,
            full_triviality_model_check=args.full_triviality_model_check,
            max_replacement_attempts=args.max_replacement_attempts,
            results_dir=Path(args.results_dir),
            worker_num_predict=args.worker_num_predict,
            ollama_timeout_seconds=args.ollama_timeout_seconds,
        )
    )
    print(
        f"Curation complete: replaced {payload['replacements']['count']} tasks, "
        f"duplicate clusters {payload['duplicates']['cluster_count_before']} -> "
        f"{payload['duplicates']['cluster_count_after']}."
    )
    print(f"Report JSON: {Path(args.results_dir) / 'curation_report.json'}")
    print(f"Report Markdown: {Path(args.results_dir) / 'curation_report.md'}")


if __name__ == "__main__":
    main()
